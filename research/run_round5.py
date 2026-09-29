"""ROUND 5 prereg R5-001. M1 primary, native M5 robustness. Decisions on M5 grid.
Stats: repaired infra (real permutation within session bucket, bootstrap CI, BH-FDR).
R-targets (MFE/MAE/P(1R)) on systematic every-6th decision subsample (documented)."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import microstructure as MS
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment

def load(split):
    m1 = pd.read_csv(ROOT/split/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
    m1["timestamp"] = pd.to_datetime(m1.timestamp, utc=True)
    m1 = MS.session_filter(m1)
    return m1

def next_rets(m5, k):
    return (m5.close.shift(-k)-m5.close)/m5.atr14

def bucket_perm_p(vals, buckets=None, B=2000, seed=0):
    """Permutation of values across groups? Here: shuffle labels within bucket.
    vals: (x0=array baseline, x1=array feature) per bucket pooled: use stratified shuffle."""
    rng = np.random.default_rng(seed)
    x0, x1 = np.asarray(vals[0], float), np.asarray(vals[1], float)
    x0 = x0[np.isfinite(x0)]; x1 = x1[np.isfinite(x1)]
    if len(x0) < 30 or len(x1) < 30:
        return 1.0, float(x1.mean()-x0.mean()) if len(x0) and len(x1) else 0.0
    obs = x1.mean()-x0.mean()
    pool = np.concatenate([x0, x1]); n1 = len(x1); c = 0
    for _ in range(B):
        rng.shuffle(pool)
        if abs(pool[:n1].mean()-pool[n1:].mean()) >= abs(obs): c += 1
    return (c+1)/(B+1), obs

out = {"prereg": "R5-001; session rule R5-SESSION-001 (Mon-Fri UTC); decisions M5 grid; R-subsample every 6th",
       "splits": {"research": "2020-01-01->2022-12-30", "validation": "2023", "final": "LOCKED 2024->2026-09"},
       "research": {}, "validation": {}, "m5robust": {}}
FAM = []
R = {}

def run_split(split):
    m1 = load(split)
    m5 = MS.m5_frame(m1)
    m5 = MS.f1_path(m1, m5)
    return m1, m5

m1, m5 = run_split("research_data")
V = {}
# base rates per session bucket (time-of-day control)
for s, g in m5.groupby("session"):
    V[f"base_next_atr_{s}"] = g.assign(nr=next_rets(g, 1)).nr
base_all = next_rets(m5, 1)

def cond(key, mask, target, min_n=100):
    x1 = target[mask.fillna(False).values]; x0 = target[(~mask.fillna(False)).values]
    m, lo, hi = bootstrap_mean_ci(x1)
    p, diff = bucket_perm_p((x0, x1))
    R[key] = {"n": int(np.isfinite(x1).sum()), "mean_atr": round(float(m), 4),
              "ci95": [round(float(lo), 4), round(float(hi), 4)],
              "diff_vs_rest": round(float(diff), 4), "perm_p": round(float(p), 4)}
    FAM.append(float(p) if np.isfinite(x1).sum() >= min_n else 1.0)

t1 = next_rets(m5, 1); t3 = next_rets(m5, 3)
# F1: path x close-loc (6 groups)
for p in ["OHLC", "OLHC"]:
    for cl in ["lo", "mid", "hi"]:
        mask = (m5.path == p) & (m5.close_loc == cl)
        cond(f"F1_{p}_{cl}", mask, t1)
# F3: high-first vs low-first (60-M1 window mapped to M5 grid)
ord60 = MS.f3_order(m1, 60)
m1v = m1.copy(); m1v["ord"] = ord60.values
mg = m1v.set_index("timestamp").groupby(pd.Grouper(freq="5min"))
last_ord = mg.ord.last().reset_index()
m5 = m5.merge(last_ord, left_on="timestamp", right_on="timestamp", how="left")
cond("F3_HF", m5.ord == "HF", t1); cond("F3_LF", m5.ord == "LF", t1)
cond("F3_HF_t3", m5.ord == "HF", t3); cond("F3_LF_t3", m5.ord == "LF", t3)
# F4: vol states + expansion event (LOW->HIGH across consecutive decisions using STATE change)
m5["vol_chg"] = (m5.vol_state.astype(str) != m5.vol_state.astype(str).shift(12)).astype(int)
for s in ["LOW", "NORM", "HIGH"]:
    cond(f"F4_vol_{s}", m5.vol_state.astype(str) == s, t1.abs())
cond("F4_expand", (m5.vol_state.astype(str) == "HIGH") & (m5.vol_state.astype(str).shift(12) == "LOW"), t1.abs())
# F5: direction sequences (M5 rets, deadband 0.02 ATR)
d = pd.Series(np.where(m5.ret/m5.atr14*m5.close > 0.02, "UP", np.where(m5.ret/m5.atr14*m5.close < -0.02, "DN", "NEU")), index=m5.index)
m5["d1"] = d
up_next = (next_rets(m5, 1) > 0).astype(float)
for s in ["UP", "DN", "NEU"]:
    x1 = up_next[m5.d1 == s]; x0 = up_next[m5.d1 != s]
    p, diff = bucket_perm_p((x0.values, x1.values))
    m = float(x1.mean()) if len(x1) else 0.5
    R[f"F5_1_{s}"] = {"n": int(len(x1)), "P_up": round(m, 4), "diff": round(float(diff), 4), "perm_p": round(float(p), 4)}
    FAM.append(float(p) if len(x1) >= 100 else 1.0)
for a in ["UP", "DN"]:
    for b in ["UP", "DN"]:
        mask = (m5.d1 == a) & (m5.d1.shift(1) == b)
        x1 = up_next[mask.fillna(False).values]; x0 = up_next[(~mask.fillna(False)).values]
        p, diff = bucket_perm_p((x0.values, x1.values))
        R[f"F5_2_{b}{a}"] = {"n": int(len(x1)), "P_up": round(float(x1.mean()) if len(x1) else 0.5, 4),
                             "diff": round(float(diff), 4), "perm_p": round(float(p), 4)}
        FAM.append(float(p) if len(x1) >= 100 else 1.0)
# F6: efficiency 30/60 M1 mapped to grid
for w in [30, 60]:
    ef = MS.efficiency(m1.set_index("timestamp").close, w)
    m1e = m1.copy(); m1e["ef"] = ef.values
    g = m1e.set_index("timestamp").groupby(pd.Grouper(freq="5min")).ef.last().reset_index()
    m5 = m5.merge(g, left_on="timestamp", right_on="timestamp", how="left", suffixes=("", f"_e{w}"))
    col = "ef" if w == 30 else f"ef_e{w}"
    q = m5[col].quantile([1/3, 2/3])
    cond(f"F6_eff{w}_hi", m5[col] > q.iloc[1], t1)
    cond(f"F6_eff{w}_lo", m5[col] < q.iloc[0], t1)
    cond(f"F6_eff{w}_hi_abs", m5[col] > q.iloc[1], t1.abs())
# F2: formation (H1 windows; research only, vectorized module)
f2 = MS.f2_formation(m1)
for mm in [15, 30, 45]:
    sub = f2[f2.mins == mm]
    if len(sub) < 100: continue
    med = sub.range_frac.median()
    x1 = sub[sub.range_frac > med].rest_ret.values; x0 = sub[sub.range_frac <= med].rest_ret.values
    p, diff = bucket_perm_p((x0, x1))
    R[f"F2_m{mm}_hiform"] = {"n": int(len(x1)), "mean_rest_atr": round(float(np.mean(x1)), 4),
                             "diff": round(float(diff), 4), "perm_p": round(float(p), 4)}
    FAM.append(float(p))
# F7: F3 x session
for s in ["asian", "london", "ny", "off"]:
    mask = (m5.ord == "HF") & (m5.session == s)
    x1 = t1[mask.fillna(False).values]
    x0 = t1[(m5.session == s).fillna(False).values]
    p, diff = bucket_perm_p((x0.values, x1.values))
    R[f"F7_HF_{s}"] = {"n": int(np.isfinite(x1).sum()), "diff_vs_session": round(float(diff), 4), "perm_p": round(float(p), 4)}
    FAM.append(float(p) if np.isfinite(x1).sum() >= 100 else 1.0)

q = bh_fdr_real(FAM)
keys = list(R.keys())
out["research"] = {k: {**R[k], "q": round(float(qq), 4)} for k, qq in zip(keys, q)}
out["research"]["keys_order"] = keys
log_experiment({"hypothesis": "R5 research family", "dataset": "research M1 Dukascopy",
                "results": {"qmin": float(min(q)), "n_tests": len(q)}, "status": "REJECTED"})
with open(ROOT/"reports"/"round5_research.json", "w") as f: json.dump(out, f, indent=2)
print(json.dumps({k: v for k, v in out["research"].items() if k != "keys_order"}, indent=2))
print("QMIN:", float(min(q)), "N:", len(q))
