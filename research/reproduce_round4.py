"""ROUND4 reproduction with REAL statistics. Same 12 hypotheses, same thresholds, same splits.
Statistic: mean(R_filtered) - mean(R_event_baseline); permutation p on observed trade-R vectors."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import volatility as V, structure as ST
from features import swings as SW
from backtesting.engine import backtest_signals
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment
import importlib.util
spec = importlib.util.spec_from_file_location("r4", ROOT/"research"/"run_round4.py")
# NOTE: run_round4 executes on import (no main guard) -> do NOT import; thresholds duplicated verbatim below.
COST = {"spread": 0.35, "slippage": 0.15}

def load_spot(split):
    df = pd.read_csv(ROOT/split/"XAUUSD_H1_duk.csv", parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    return V.add_volatility(ST.add_structure(df, SW.fractal_swings(df, 2)))

def macro_feats():
    feats = {}
    for k in ["DXY","Y10","YSHORT","VIX","SPX","OIL","TIP"]:
        m = pd.read_csv(ROOT/"data"/"raw"/f"MACRO_{k}_D1.csv", parse_dates=["timestamp"])
        m["timestamp"] = pd.to_datetime(m.timestamp, utc=True)
        m = m.sort_values("timestamp")
        m["ret1"] = m.close.pct_change(1); m["ret5"] = m.close.pct_change(5)
        m["pct252"] = m.close.rolling(252).rank(pct=True)
        m["trend50"] = np.sign(m.close-m.close.shift(50))
        m["date"] = m.timestamp.dt.date
        feats[k] = m[["date","ret1","ret5","pct252","trend50"]].rename(
            columns={c: f"{k}_{c}" for c in ["ret1","ret5","pct252","trend50"]})
    return feats

def attach(df, feats):
    df = df.copy(); df["date"] = pd.to_datetime(df.timestamp).dt.date
    cal = pd.DataFrame({"date": sorted(df.date.unique())})
    for k, f in feats.items(): cal = cal.merge(f, on="date", how="left")
    cal = cal.sort_values("date")
    for c in cal.columns:
        if c != "date": cal[c] = cal[c].ffill()
    sh = cal.copy()
    for c in cal.columns:
        if c != "date": sh[c] = cal[c].shift(1)
    return df.merge(sh, on="date", how="left")

def detect(df):
    h,l,c,a = df.high,df.low,df.close,df.atr
    df2 = df.copy()
    df2["prev20hi"] = h.shift(1).rolling(20).max()
    n = len(df2); sw_h,sw_l,bo_up,bo_dn,fb=[],[],[],[],[]
    pl_series=l.shift(1).rolling(20).min()
    for i in range(25,n-1):
        if not np.isfinite(a.iloc[i]) or a.iloc[i]<=0: continue
        ph=df2.prev20hi.iloc[i]; pl=pl_series.iloc[i]
        if h.iloc[i]>ph and (h.iloc[i]-ph)<0.25*a.iloc[i] and c.iloc[i]<ph: sw_h.append({"idx":i+1,"direction":-1})
        if l.iloc[i]<pl and (pl-l.iloc[i])<0.25*a.iloc[i] and c.iloc[i]>pl: sw_l.append({"idx":i+1,"direction":1})
        if c.iloc[i]>ph: bo_up.append({"idx":i+1,"direction":1})
        if c.iloc[i]<pl: bo_dn.append({"idx":i+1,"direction":-1})
    bos={r["idx"]-1:r["direction"] for r in bo_up+bo_dn}
    pl2=l.shift(1).rolling(20).min()
    for i,d in bos.items():
        if i+4>=n: continue
        lv=df2.prev20hi.iloc[i] if d==1 else pl2.iloc[i]
        for k in range(i+1,min(i+4,n-1)):
            back = c.iloc[k]<lv if d==1 else c.iloc[k]>lv
            if back: fb.append({"idx":k+1,"direction":-d}); break
    S=lambda r: pd.DataFrame(r) if r else pd.DataFrame(columns=["idx","direction"])
    return {"sweep_high":S(sw_h),"sweep_low":S(sw_l),"breakout_up":S(bo_up),"breakout_down":S(bo_dn),"failed_breakout":S(fb)}

def R_of(df, sig):
    sig = sig[sig.idx < len(df)-1]
    if len(sig) == 0: return np.array([])
    tr = backtest_signals(df, sig, 1.5, 2.0, 20, COST["spread"], COST["slippage"])
    return tr.R.values if len(tr) else np.array([])

INTER = [
    ("breakout_up","DXY_ret1",-1),("breakout_up","DXY_trend50",-1),
    ("breakout_up","Y10_ret1",-1),("breakout_up","Y10_ret5",-1),
    ("sweep_high","DXY_ret1",+1),("sweep_high","Y10_ret1",+1),
    ("breakout_up","VIX_pct252","hi"),("breakout_up","SPX_ret1",+1),
    ("sweep_high","VIX_pct252","hi"),("failed_breakout","DXY_ret1","any"),
    ("breakout_up","TIP_ret1",+1),("breakout_up","OIL_ret1",+1),
]
feats = macro_feats()
out = {"research": {}, "validation": {}}
P, Q = [], []
for split in ["research_data", "validation_data"]:
    df = attach(load_spot(split), feats)
    ev = detect(df)
    for name, col, need in INTER:
        sig = ev[name]
        base = R_of(df, sig)
        if len(sig) and col != "DXY_ret1_any_placeholder":
            idx = sig.idx.clip(0, len(df)-1)
            if need == "any":
                mask = np.ones(len(sig), bool); filt = np.array([])
            elif col == "VIX_pct252":
                mask = (df[col].iloc[idx].values > 0.8); filt = R_of(df, sig[np.asarray(mask)])
            else:
                mask = np.sign(df[col].iloc[idx].values) == need; filt = R_of(df, sig[np.asarray(mask)])
        else:
            filt = np.array([])
        m, lo, hi = bootstrap_mean_ci(filt)
        p, obs = permutation_diff_p(filt, base)
        key = f"{name}_x_{col}={need}"
        rec = {"n_filt": int(len(filt)), "n_base": int(len(base)),
               "mean_filt": round(float(m), 4) if filt.size else None,
               "ci95": [round(float(lo), 4), round(float(hi), 4)] if filt.size else None,
               "obs_diff": round(float(obs), 4), "perm_p": round(float(p), 4)}
        out["validation" if split == "validation_data" else "research"][f"{split[:3]}_{key}"] = rec
        if split == "research_data": P.append(float(p))
q = bh_fdr_real(P)
out["FDR_real"] = {"p": [round(float(x), 4) for x in P], "q": [round(float(x), 4) for x in q]}
log_experiment({"hypothesis": "R4 reproduction with real stats", "dataset": "research->validation spot+macro",
                "results": {"qmin": float(min(q)), "pmin": float(min(P))}, "status": "REJECTED"})
with open(ROOT/"reports"/"round4_repaired.json", "w") as f: json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
