"""R5 validation + M5-native robustness + F8 info gain + R-targets + spread economics."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import microstructure as MS
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment

def build(split):
    m1 = pd.read_csv(ROOT/split/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
    m1["timestamp"] = pd.to_datetime(m1.timestamp, utc=True)
    m1 = MS.session_filter(m1)
    m5 = MS.m5_frame(m1)
    m5 = MS.f1_path(m1, m5)
    return m1, m5

def t1(m5): return (m5.close.shift(-1)-m5.close)/m5.atr14
def t3(m5): return (m5.close.shift(-3)-m5.close)/m5.atr14

m1v, m5v = build("validation_data")
T1, T3 = t1(m5v), t3(m5v)
ord60 = MS.f3_order(m1v, 60)
m1v2 = m1v.copy(); m1v2["ord"] = ord60.values
last_ord = m1v2.set_index("timestamp").groupby(pd.Grouper(freq="5min")).ord.last().reset_index()
m5v = m5v.merge(last_ord, left_on="timestamp", right_on="timestamp", how="left")
d = pd.Series(np.where(m5v.ret/m5v.atr14*m5v.close > 0.02, "UP",
              np.where(m5v.ret/m5v.atr14*m5v.close < -0.02, "DN", "NEU")), index=m5v.index)
m5v["d1"] = d
up_next = (t1(m5v) > 0).astype(float)
out = {"validation": {}, "m5robust": {}, "f8": {}, "R": {}, "econ": {}}
P = []

def rec(key, x1, x0, kind="mean"):
    x1 = np.asarray(x1, float); x1 = x1[np.isfinite(x1)]
    x0 = np.asarray(x0, float); x0 = x0[np.isfinite(x0)]
    if kind == "mean":
        m, lo, hi = bootstrap_mean_ci(x1)
        stat = {"mean_atr": round(float(m), 4), "ci95": [round(float(lo), 4), round(float(hi), 4)]}
    else:
        stat = {"P_up": round(float(x1.mean()) if len(x1) else 0.5, 4)}
    p, diff = permutation_diff_p(x1, x0)  # diff = feature - rest (matches research file)
    out["validation"][key] = {"n": int(len(x1)), **stat, "diff": round(float(diff), 4), "perm_p": round(float(p), 4)}
    P.append(float(p) if len(x1) >= 100 else 1.0)

# same 19 survivors, identical definitions
rec("F1_OHLC_lo", T1[(m5v.path == "OHLC") & (m5v.close_loc == "lo")], T1[~((m5v.path == "OHLC") & (m5v.close_loc == "lo"))])
rec("F1_OLHC_mid", T1[(m5v.path == "OLHC") & (m5v.close_loc == "mid")], T1[~((m5v.path == "OLHC") & (m5v.close_loc == "mid"))])
rec("F3_HF", T1[m5v.ord == "HF"], T1[m5v.ord != "HF"])
rec("F3_LF", T1[m5v.ord == "LF"], T1[m5v.ord != "LF"])
rec("F3_HF_t3", T3[m5v.ord == "HF"], T3[m5v.ord != "HF"])
rec("F3_LF_t3", T3[m5v.ord == "LF"], T3[m5v.ord != "LF"])
for s in ["LOW", "NORM", "HIGH"]:
    rec(f"F4_vol_{s}", T1.abs()[m5v.vol_state.astype(str) == s], T1.abs()[m5v.vol_state.astype(str) != s])
for s in ["UP", "DN"]:
    rec(f"F5_1_{s}", up_next[m5v.d1 == s], up_next[m5v.d1 != s], kind="p")
for a in ["UP", "DN"]:
    for b in ["UP", "DN"]:
        m = (m5v.d1 == a) & (m5v.d1.shift(1) == b)
        rec(f"F5_2_{b}{a}", up_next[m.fillna(False).values], up_next[(~m.fillna(False)).values], kind="p")
for w, col in [(30, "ef"), (60, "ef_e60")]:
    ef = MS.efficiency(m1v.set_index("timestamp").close, w)
    m1e = m1v.copy(); m1e["ef"] = ef.values
    g = m1e.set_index("timestamp").groupby(pd.Grouper(freq="5min")).ef.last().reset_index()
    m5v = m5v.merge(g, left_on="timestamp", right_on="timestamp", how="left", suffixes=("", f"_v{w}"))
    c = "ef" if w == 30 else f"ef_v{w}"
    qq = m5v[c].quantile([1/3, 2/3])
    rec(f"F6_eff{w}_hi_abs", T1.abs()[m5v[c] > qq.iloc[1]], T1.abs()[m5v[c] <= qq.iloc[1]])
    if w == 60:
        rec("F6_eff60_hi", T1[m5v[c] > qq.iloc[1]], T1[m5v[c] <= qq.iloc[1]])
m = (m5v.ord == "HF") & (m5v.session == "off")
rec("F7_HF_off", T1[m.fillna(False).values], T1[(m5v.session == "off").fillna(False).values])
q = bh_fdr_real(P)
for k, qq in zip(list(out["validation"].keys()), q):
    out["validation"][k]["q"] = round(float(qq), 4)

# M5-native robustness (M5-only inputs): F3m order in trailing 12 M5; F6m eff over 12 M5; F1m path of H1 from 12 M5... use H1 grouping
m5n = m5v.copy()
h = m5n.high.rolling(12, min_periods=12).apply(lambda x: int(np.argmax(x)), raw=True)
l = m5n.low.rolling(12, min_periods=12).apply(lambda x: int(np.argmin(x)), raw=True)
m5n["ord12"] = np.where(h < l, "HF", "LF")
for grp, col in [("HF", "ord12")]:
    x1 = T1[m5n[col] == grp]; x0 = T1[m5n[col] != grp]
    p, diff = permutation_diff_p(x0.values, x1.values)
    m_, lo, hi = bootstrap_mean_ci(x1.values)
    out["m5robust"][f"F3m_{grp}"] = {"n": int(np.isfinite(x1).sum()), "mean_atr": round(float(m_), 4),
        "diff": round(float(diff), 4), "perm_p": round(float(p), 4)}
net = (m5n.close-m5n.close.shift(12)).abs(); path = m5n.close.diff().abs().rolling(12, min_periods=12).sum()
m5n["ef12"] = net/(path+1e-12)
qq = m5n.ef12.quantile([1/3, 2/3])
for side, mk in [("hi", m5n.ef12 > qq.iloc[1]), ("lo", m5n.ef12 < qq.iloc[0])]:
    x1 = T1[mk.fillna(False).values]; x0 = T1[(~mk.fillna(False)).values]
    p, diff = permutation_diff_p(x0.values, x1.values)
    out["m5robust"][f"F6m_{side}"] = {"n": int(np.isfinite(x1).sum()), "diff": round(float(diff), 4), "perm_p": round(float(p), 4)}
# F1m: H1-bar path from twelve M5 bars -> NEXT-H1 return (M5-only analogue of F1)
m5n["h1"] = pd.to_datetime(m5n.timestamp).dt.floor("h")
hret = m5n.groupby("h1").agg(o=("open", "first"), c=("close", "last"))
hret["next_ret"] = (hret.c.shift(-1)-hret.c)/hret.c
rows = []
for h, g in m5n.groupby("h1"):
    if len(g) < 10: continue
    hi = g.high.values.argmax(); lo = g.low.values.argmin()
    cls = "OHLC" if hi < lo else "OLHC"
    nr = hret.next_ret.get(h, np.nan)
    rows.append({"ts": g.timestamp.iloc[-1], "cls": cls, "ret_next": float(nr) if np.isfinite(nr) else np.nan})
f1m = pd.DataFrame(rows)
for cls in ["OHLC", "OLHC"]:
    x1 = f1m[f1m.cls == cls].ret_next.values; x0 = f1m[f1m.cls != cls].ret_next.values
    p, diff = permutation_diff_p(x0, x1)
    out["m5robust"][f"F1m_{cls}"] = {"n": int(np.isfinite(x1).sum()), "diff": round(float(diff), 4), "perm_p": round(float(p), 4)}

# F8 info gain: A H1-only vs B +M5 vs C +M1, target next-M5 up; train research, test validation
def h1frame(m1x):
    g = m1x.set_index("timestamp")
    o = g.open.resample("h").first(); h = g.high.resample("h").max(); l = g.low.resample("h").min(); c = g.close.resample("h").last()
    h1 = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna()
    tr = (h1.high-h1.low)
    h1["atr"] = tr.rolling(14, min_periods=14).mean()
    h1["ret1"] = h1.close.pct_change()
    h1["cloc"] = (h1.close-h1.low)/(h1.high-h1.low+1e-12)
    return h1
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
def build_xy(split):
    m1x = pd.read_csv(ROOT/split/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
    m1x["timestamp"] = pd.to_datetime(m1x.timestamp, utc=True)
    m1x = MS.session_filter(m1x)
    m5x = MS.m5_frame(m1x); m5x = MS.f1_path(m1x, m5x)
    h1 = h1frame(m1x)
    hx = h1.reindex(pd.DatetimeIndex(pd.to_datetime(m5x.timestamp).dt.floor("h").values).tz_localize("UTC"))
    m5x = m5x.copy()
    m5x["h_ret"] = hx.ret1.values; m5x["h_rng"] = ((hx.high-hx.low)/hx.atr).values; m5x["h_cloc"] = hx.cloc.values
    m5x["tod"] = pd.to_datetime(m5x.timestamp).dt.hour
    m5x["d_up"] = (m5x.ret > 0).astype(int)
    o = MS.f3_order(m1x, 60)
    m1x["ord"] = o.values
    mo = m1x.set_index("timestamp").groupby(pd.Grouper(freq="5min")).ord.last().reset_index()
    m5x = m5x.merge(mo, left_on="timestamp", right_on="timestamp", how="left")
    ef = MS.efficiency(m1x.set_index("timestamp").close, 60)
    m1x["ef"] = ef.values
    me = m1x.set_index("timestamp").groupby(pd.Grouper(freq="5min")).ef.last().reset_index()
    m5x = m5x.merge(me, left_on="timestamp", right_on="timestamp", how="left", suffixes=("", "_e"))
    y = ((m5x.close.shift(-1)-m5x.close) > 0).astype(int)
    A = pd.DataFrame({"h_ret": m5x.h_ret, "h_rng": m5x.h_rng, "h_cloc": m5x.h_cloc, "tod": m5x.tod}).fillna(0)
    B = A.assign(m_ret=m5x.ret.fillna(0), d_up=m5x.d_up, volhi=(m5x.vol_state.astype(str) == "HIGH").astype(int))
    C = B.assign(ohlc=(m5x.path == "OHLC").astype(int), hf=(m5x.ord == "HF").astype(int), ef=m5x.ef.fillna(0.5))
    msk = m5x.atr14.notna() & m5x.h_ret.notna()
    return A[msk], B[msk], C[msk], y[msk]
Atr, Btr, Ctr, ytr = build_xy("research_data")
Ava, Bva, Cva, yva = build_xy("validation_data")
f8 = {}
for nm, pair in [("A", (Atr, Ava)), ("B", (Btr, Bva)), ("C", (Ctr, Cva))]:
    Xtr, Xva = pair
    m = LogisticRegression(max_iter=1000).fit(Xtr, ytr)
    pr = m.predict_proba(Xva)[:, 1]
    f8[nm] = {"auc": round(float(roc_auc_score(yva, pr)), 4), "brier": round(float(brier_score_loss(yva, pr)), 4),
              "logloss": round(float(log_loss(yva, pr)), 4)}
rng = np.random.default_rng(0)
for pair in [("C", "A"), ("B", "A"), ("C", "B")]:
    X1, X0 = {"A": Ava, "B": Bva, "C": Cva}[pair[0]], {"A": Ava, "B": Bva, "C": Cva}[pair[0]]
mA = LogisticRegression(max_iter=1000).fit(Atr, ytr).predict_proba(Ava)[:, 1]
mC = LogisticRegression(max_iter=1000).fit(Ctr, ytr).predict_proba(Cva)[:, 1]
bs = []
for _ in range(500):
    i = rng.choice(len(yva), size=len(yva), replace=True)
    bs.append(roc_auc_score(yva.iloc[i], mC[i])-roc_auc_score(yva.iloc[i], mA[i]))
f8["C_minus_A_AUC_CI95"] = [round(float(np.quantile(bs, .025)), 4), round(float(np.quantile(bs, .975)), 4)]
out["f8"] = f8

# R-targets on every-6th decision for F3/F5 groups (fixed 1.5ATR risk, TP 1R/SL 1R race on M1 path)
H = m1v.high.values; L = m1v.low.values; Cc = m1v.close.values; Av = m1v.atr14.values if "atr14" in m1v else None
from features import volatility as V
m1a = V.add_volatility(m1v)
Av = m1a.atr.values
tsidx = {t: i for i, t in enumerate(m1v.timestamp)}
dec = m5v.iloc[::6].reset_index(drop=True)
grp = {"F3_HF": (dec.ord == "HF").values, "F3_LF": (dec.ord == "LF").values,
       "F5_DN": (dec.d1 == "DN").values, "F5_UP": (dec.d1 == "UP").values}
rng0 = np.random.default_rng(0)
rand_mask = np.zeros(len(dec), bool)
ridx = rng0.choice(len(dec), size=int(len(dec)/4), replace=False)
rand_mask[ridx] = True
grp["RAND"] = rand_mask
rdir = np.random.default_rng(1).choice([-1, 1], size=len(dec))
for gi, (gk, mk) in enumerate(grp.items()):
    wins = 0; n = 0; mfes = []; maes = []
    for j in np.where(mk)[0]:
        ts = dec.timestamp.iloc[j]
        i = tsidx.get(ts, None)
        if i is None or i+60 >= len(Cc): continue
        a = Av[i]
        if not np.isfinite(a) or a <= 0: continue
        # F3 tests continuation (HF->long, LF->short); F5 tests the reversal finding (DN->long, UP->short)
        dirc = rdir[j] if gk == "RAND" else (1 if gk in ("F3_HF", "F5_DN") else -1)
        entry = Cc[i]; risk = 1.5*a
        up = entry+dirc*1.0*risk; dn = entry-dirc*1.0*risk
        res = None
        for k in range(i+1, min(i+61, len(Cc))):
            hit_up = (H[k] >= up) if dirc == 1 else (L[k] <= up)
            hit_dn = (L[k] <= dn) if dirc == 1 else (H[k] >= dn)
            if hit_up and hit_dn: res = 0; break
            if hit_up: res = 1; break
            if hit_dn: res = 0; break
        if res is None: continue
        n += 1; wins += res
        if dirc == 1:
            mfes.append((H[i+1:i+61].max()-entry)/risk); maes.append((L[i+1:i+61].min()-entry)/risk)
        else:
            mfes.append((entry-L[i+1:i+61].min())/risk); maes.append((entry-H[i+1:i+61].max())/risk)
    out["R"][gk] = {"n": n, "P_1R_before_1R": round(wins/n, 4) if n else None,
                    "MFE_med": round(float(np.median(mfes)), 3) if mfes else None,
                    "MAE_med": round(float(np.median(maes)), 3) if maes else None}
med_atr_usd = float(m5v.atr14.median())
out["econ"] = {"median_M5_ATR_usd": round(med_atr_usd, 3),
               "note": "0.026 ATR directional effect over 3 M5 bars; spread 0.35 + slippage 0.15 assumed"}
log_experiment({"hypothesis": "R5 validation+M5+F8+R", "dataset": "validation M1 Dukascopy",
                "results": {"f8": f8, "qmin_val": float(min(q))}, "status": "REJECTED"})
with open(ROOT/"reports"/"round5_validation.json", "w") as f: json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
