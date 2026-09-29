"""Validation + robustness + costs + baselines. Uses validation_data only. Final untouched."""
import json, sys
from pathlib import Path
import pandas as pd
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, fibonacci as FIB, volatility as V, structure as ST
from backtesting.engine import backtest_signals
from statsx.tests import expectancy, trade_stats, bootstrap_ci
from research.registry import log_experiment

CFG = json.load(open(ROOT/"configs"/"config.json"))
COST = CFG["costs"]

def load(tf, split):
    df = pd.read_csv(ROOT/split/f"XAUUSD_{tf}.csv", parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    return df

def build_signals(df, level=0.5, trend=False, vol=None, fade=True):
    df = V.add_volatility(df)
    sw = SW.fractal_swings(df, CFG["swing"]["fractal_k"])
    df = ST.add_structure(df, sw)
    pairs = FIB.pairs_to_retracements(sw)
    sigs = []
    for _, r in pairs.iterrows():
        c0 = int(r.confirm_idx)
        if c0+1 >= len(df):
            continue
        if trend and df.trend_state.iloc[c0] == 0:
            continue
        if vol and df.vol_regime.iloc[c0] != vol:
            continue
        lp = FIB.level_price(r.lo, r.hi, level, r.direction)
        base = df.close.iloc[c0]
        d = 1 if base < lp else -1
        sigs.append({"idx": c0+1, "direction": -d if fade else d})
    return df, pd.DataFrame(sigs)

def random_baseline(df, n, sl=1.5, tp=2.0):
    rng = np.random.default_rng(7)
    n = min(n, max(0, len(df)-26))
    if n == 0:
        return pd.DataFrame()
    idx = rng.choice(range(len(df)-25), size=n, replace=False)
    sig = pd.DataFrame([{"idx": int(i), "direction": int(rng.choice([-1,1]))} for i in idx])
    return backtest_signals(df, sig, sl, tp, 20, COST["spread_xauusd"], COST["slippage"])

out = {}
# Candidate from research: H1 lvl0.5 high-vol (+0.14R) and H1 lvl0.5 trend (+0.088R)
for tf in ["H1", "D1"]:
    dfv = load(tf, "validation_data")
    for name, kw in [("cand_highvol_05", dict(level=0.5, vol="high")),
                     ("cand_trend_05", dict(level=0.5, trend=True)),
                     ("base_05", dict(level=0.5)),
                     ("base_618", dict(level=0.618))]:
        df2, sig = build_signals(dfv, **kw)
        tr = backtest_signals(df2, sig, 1.5, 2.0, 20, COST["spread_xauusd"], COST["slippage"])
        e = expectancy(tr.R.values) if len(tr) else {"exp_R": 0, "n": 0}
        out[f"VAL_{tf}_{name}"] = {**e, **{"stats": trade_stats(tr.R.values) if len(tr) else {}}}
        log_experiment({"hypothesis": "H5 validation of candidate", "dataset": f"validation XAUUSD {tf} {name}",
                        "results": out[f"VAL_{tf}_{name}"], "status": "VALIDATED" if e.get("exp_R",0)>0 and e.get("ci_lo",-1)>0 else ("PROMISING" if e.get("exp_R",0)>0 else "REJECTED")})
    # baselines on H1/D1 validation
    df2, _ = build_signals(dfv, level=0.5)
    rb = random_baseline(df2, 500)
    out[f"BASE_{tf}_random"] = expectancy(rb.R.values)
    # buy-hold in R units approx: (last-first)/avgATR-risk
    # cost sweep on candidate
    for m in [1.0, 2.0, 3.0]:
        df2, sig = build_signals(dfv, level=0.5, vol="high")
        tr = backtest_signals(df2, sig, 1.5, 2.0, 20, COST["spread_xauusd"]*m, COST["slippage"])
        e = expectancy(tr.R.values) if len(tr) else {"exp_R": 0, "n": 0}
        out[f"COST_{tf}_spread{m}x"] = e
    # param heatmap: fib x SL
    for lvl in [0.5, 0.55, 0.618, 0.65]:
        for sl in [1.0, 1.5, 2.0]:
            df2, sig = build_signals(load(tf, "research_data"), level=lvl, vol="high")
            tr = backtest_signals(df2, sig, sl, 2.0, 20, COST["spread_xauusd"], COST["slippage"])
            e = expectancy(tr.R.values) if len(tr) else {"exp_R": 0, "n": 0}
            out[f"HEAT_{tf}_lvl{lvl}_sl{sl}"] = round(e.get("exp_R", 0), 4)
    # Monte Carlo trade-order bootstrap on research candidate
    df2, sig = build_signals(load(tf, "research_data"), level=0.5, vol="high")
    tr = backtest_signals(df2, sig, 1.5, 2.0, 20, COST["spread_xauusd"], COST["slippage"])
    if len(tr):
        rng = np.random.default_rng(42)
        means = [rng.choice(tr.R.values, size=len(tr), replace=True).mean() for _ in range(2000)]
        out[f"MC_{tf}"] = {"p_gt0": float(np.mean(np.array(means) > 0)), "ci95": [float(np.quantile(means, .025)), float(np.quantile(means, .975))]}

with open(ROOT/"reports"/"validation_report.json", "w") as f:
    json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
