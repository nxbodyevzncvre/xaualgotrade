"""TICK-SPREAD VERIFICATION (prereg reports/PREREG_TICK_SPREAD.md).
Order: research characterization (2020-22) -> validation calc (2023). 2024+ never read.
FDR family = 6 directional F5 cells (NEU reported descriptively; it has no fade direction)."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import microstructure as MS
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment

AGG = ROOT/"data"/"raw"/"_tickagg"
DIR6 = ["UP", "DN", "UPUP", "DNUP", "UPDN", "DNDN"]

def load_minutes(years):
    frames = []
    for y in years:
        for m in range(1, 13):
            p = AGG/f"min_{y}{m:02d}.csv"
            if not p.exists():
                raise FileNotFoundError(f"missing {p} — run dl_tick for {y}-{m:02d}")
            frames.append(pd.read_csv(p, parse_dates=["timestamp"]))
    df = pd.concat(frames).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    wd = df.timestamp.dt.weekday
    return df[(wd < 5)].reset_index(drop=True)  # R5-SESSION-001

def to_m5(minute_df, col="mid_close"):
    g = minute_df.set_index("timestamp")
    o = g[col].resample("5min").first(); h = g[col].resample("5min").max()
    l = g[col].resample("5min").min(); c = g[col].resample("5min").last()
    sp = g["spread_mean"].resample("5min").mean()
    nt = g["n_ticks"].resample("5min").sum()
    m5 = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "spread": sp, "n_ticks": nt}).dropna().reset_index()
    m5 = MS.add_sessions(m5)
    tr = pd.concat([m5.high-m5.low, (m5.high-m5.close.shift(1)).abs(),
                    (m5.low-m5.close.shift(1)).abs()], axis=1).max(axis=1)
    m5["atr14"] = tr.rolling(14, min_periods=14).mean()
    m5["ret"] = m5.close.pct_change()
    m5["vol_state"] = m5.ret.rolling(240, min_periods=240).std().rolling(2000, min_periods=2000).rank(pct=True)
    m5["vol_state"] = pd.cut(m5.vol_state, [0, .33, .66, 1.0], labels=["LOW", "NORM", "HIGH"])
    d = pd.Series(np.where(m5.ret/m5.atr14*m5.close > 0.02, "UP",
                  np.where(m5.ret/m5.atr14*m5.close < -0.02, "DN", "NEU")), index=m5.index)
    m5["d1"] = d
    return m5

def masks(m5):
    d1, d0 = m5.d1, m5.d1.shift(1)
    return {"UP": d1 == "UP", "DN": d1 == "DN", "NEU": d1 == "NEU",
            "UPUP": (d1 == "UP") & (d0 == "UP"), "DNUP": (d1 == "UP") & (d0 == "DN"),
            "UPDN": (d1 == "DN") & (d0 == "UP"), "DNDN": (d1 == "DN") & (d0 == "DN")}

def spread_cells(minute_df, m5):
    key = minute_df.timestamp.dt.floor("5min")
    st = m5.set_index("timestamp")
    out = {}
    for s in ["asian", "london", "ny", "off"]:
        for v in ["LOW", "NORM", "HIGH"]:
            for f in ["UP", "DN", "NEU"]:
                lab = st[(st.session == s) & (st.vol_state.astype(str) == v) & (st.d1 == f)].index
                vals = minute_df[minute_df.timestamp.dt.floor("5min").isin(lab)].spread_mean.values
                if len(vals) == 0: continue
                out[f"{s}/{v}/{f}"] = {"n_min": int(len(vals)),
                    "mean": round(float(vals.mean()), 4), "median": round(float(np.median(vals)), 4),
                    "p90": round(float(np.quantile(vals, .9)), 4)}
    return out

def signflip_p(x, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 30: return 1.0, float(x.mean()) if len(x) else 0.0
    obs = x.mean(); c = sum(abs((x*rng.choice([-1., 1.], size=len(x))).mean()) >= abs(obs) for _ in range(B))
    return (c+1)/(B+1), obs

out = {"spread_cells_research": {}, "spread_cells_validation": {},
       "gross_bid": {}, "mid_genuine": {}, "artifact": {}, "net": {}, "decision": None}

# ---- 1. research-side spread characterization (2020-22) ----
min_r = load_minutes([2020, 2021, 2022])
m5_r = to_m5(min_r)
out["spread_cells_research"] = spread_cells(min_r, m5_r)
all_r = min_r.spread_mean.values
out["spread_cells_research"]["__overall__"] = {"n_min": int(len(all_r)),
    "mean": round(float(all_r.mean()), 4), "median": round(float(np.median(all_r)), 4),
    "p90": round(float(np.quantile(all_r, .9)), 4)}
print("research spread overall:", out["spread_cells_research"]["__overall__"], flush=True)

# ---- 2. validation (2023): gross bid replication + mid genuine + artifact + net ----
min_v = load_minutes([2023])
m5_mid = to_m5(min_v)
# bid M5 for 2023 from existing bid file (R5-exact path)
bid = pd.read_csv(ROOT/"validation_data"/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
bid["timestamp"] = pd.to_datetime(bid.timestamp, utc=True)
bid = MS.session_filter(bid)
gb = bid.set_index("timestamp").close.resample("5min").last()
m5_bid = pd.DataFrame({"close": gb}).dropna().reset_index()
m5_bid = MS.add_sessions(m5_bid)
m5 = m5_mid.merge(m5_bid[["timestamp", "close"]].rename(columns={"close": "bid_close"}), on="timestamp", how="inner")
m5["bid_ret"] = m5.bid_close.pct_change()
m5["bid_atr"] = m5.bid_close.diff().abs().rolling(14, min_periods=14).mean()  # proportional ATR on bid closes
mm = masks(m5)
out["spread_cells_validation"] = spread_cells(min_v, m5_mid)
all_v = min_v.spread_mean.values
out["spread_cells_validation"]["__overall__"] = {"n_min": int(len(all_v)),
    "mean": round(float(all_v.mean()), 4), "median": round(float(np.median(all_v)), 4),
    "p90": round(float(np.quantile(all_v, .9)), 4)}
print("validation spread overall:", out["spread_cells_validation"]["__overall__"], flush=True)

P = []
for cell in DIR6:
    mk = mm[cell].fillna(False).values
    # gross bid: next-M5 bid return in bid-ATR units
    ba = m5.bid_atr.values
    br = m5.bid_ret.values/ba
    ma = m5.atr14.values
    mr = m5_mid.set_index("timestamp").ret.reindex(
        pd.DatetimeIndex(m5.timestamp.values).tz_localize("UTC")).values/ma
    g = br[1:][mk[1:]] if len(br) > 1 else np.array([])
    m_ = mr[1:][mk[1:]] if len(mr) > 1 else np.array([])
    g = g[np.isfinite(g)]; m_ = m_[np.isfinite(m_)]
    mg, glo, ghi = bootstrap_mean_ci(g); mm_, mlo, mhi = bootstrap_mean_ci(m_)
    d = g[:len(m_)]-m_[:len(g)] if len(g) and len(m_) else np.array([])
    md, dlo, dhi = bootstrap_mean_ci(d)
    out["gross_bid"][cell] = {"n": int(len(g)), "mean_atr": round(float(mg), 4),
                              "ci95": [round(float(glo), 4), round(float(ghi), 4)]}
    out["mid_genuine"][cell] = {"n": int(len(m_)), "mean_atr": round(float(mm_), 4),
                                "ci95": [round(float(mlo), 4), round(float(mhi), 4)]}
    out["artifact"][cell] = {"n": int(len(d)), "mean_atr": round(float(md), 4),
                             "ci95": [round(float(dlo), 4), round(float(dhi), 4)]}
    # net fade: fade UP* -> short(-1); fade DN* -> long(+1)
    direction = -1 if cell in ("UP", "UPUP", "DNUP") else 1
    ce = m5.close.values[:-1][mk[:-1]]; cx = m5.close.values[1:][mk[:-1]]
    se = m5.spread.values[:-1][mk[:-1]]; sx = m5.spread.values[1:][mk[:-1]]
    ae = ma[:-1][mk[:-1]]
    ok = np.isfinite(ce) & np.isfinite(cx) & np.isfinite(se) & np.isfinite(sx) & np.isfinite(ae) & (ae > 0)
    net_usd = direction*(cx[ok]-ce[ok])-(se[ok]+sx[ok])/2
    net_atr = net_usd/ae[ok]
    mn, nlo, nhi = bootstrap_mean_ci(net_atr)
    p, obs = signflip_p(net_atr)
    out["net"][cell] = {"n": int(ok.sum()), "mean_usd": round(float(net_usd.mean()) if ok.sum() else 0, 4),
                        "mean_atr": round(float(mn), 4), "ci95": [round(float(nlo), 4), round(float(nhi), 4)],
                        "p": round(float(p), 4)}
    P.append(float(p) if ok.sum() >= 30 else 1.0)

q = bh_fdr_real(P)
for k, qq in zip(DIR6, q):
    out["net"][k]["q"] = round(float(qq), 4)
# D2 requires net CI strictly positive (same sign as research fade-implied edge) + q<0.10
ok_cells = [k for k in DIR6 if out["net"][k]["ci95"][0] > 0 and out["net"][k]["q"] < 0.10]
if not ok_cells:
    out["decision"] = "D1: all net CIs include 0 or q>=0.10 -> F5 = quote artifact or sub-cost noise. STOP stands."
else:
    out["decision"] = f"D2: candidate cells {ok_cells} (phenomenon, NOT strategy). No 2024+ inspection."
log_experiment({"hypothesis": "tick-spread verification", "dataset": "2023 validation tick; 2020-22 research",
                "results": {"qmin": float(min(q)), "decision": out["decision"]}, "status": "REJECTED"})
with open(ROOT/"reports"/"tickspread.json", "w") as f: json.dump(out, f, indent=2)
print(json.dumps({"net": out["net"], "decision": out["decision"]}, indent=2))
