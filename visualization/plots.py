"""Plots: equity/drawdown/MFE/heatmap. Random trade examples noted, aggregate stats = evidence."""
import json
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(ROOT))
from features import swings as SW, fibonacci as FIB, volatility as V, structure as ST
from backtesting.engine import backtest_signals
CFG = json.load(open(ROOT/"configs"/"config.json"))

def rebuild(df):
    df = V.add_volatility(df)
    sw = SW.fractal_swings(df, 2)
    df = ST.add_structure(df, sw)
    pairs = FIB.pairs_to_retracements(sw)
    sigs = []
    for _, r in pairs.iterrows():
        c0 = int(r.confirm_idx)
        if c0+1 >= len(df): continue
        if df.vol_regime.iloc[c0] != "high": continue
        lp = FIB.level_price(r.lo, r.hi, 0.5, r.direction)
        d = 1 if df.close.iloc[c0] < lp else -1
        sigs.append({"idx": c0+1, "direction": -d})
    tr = backtest_signals(df, pd.DataFrame(sigs), 1.5, 2.0, 20, 0.35, 0.15)
    return tr

for tf, split in [("H1","research_data"), ("H1","final_test_data")]:
    df = pd.read_csv(ROOT/split/f"XAUUSD_{tf}.csv", parse_dates=["timestamp"])
    tr = rebuild(df)
    if len(tr) == 0: continue
    eq = tr.R.cumsum()
    dd = eq - eq.cummax()
    fig, ax = plt.subplots(2, 1, figsize=(10,6), sharex=True)
    ax[0].plot(eq.values); ax[0].set_title(f"Equity (R) XAUUSD {tf} {split} n={len(tr)} exp={tr.R.mean():.3f}R")
    ax[1].fill_between(range(len(dd)), dd.values, 0, alpha=.4); ax[1].set_title("Drawdown (R)")
    fig.tight_layout(); fig.savefig(ROOT/f"reports/equity_{tf}_{split}.png", dpi=100); plt.close(fig)
    fig, ax = plt.subplots(1,2, figsize=(10,4))
    ax[0].hist(tr.MFE.values, bins=30); ax[0].set_title("MFE (R)")
    ax[1].hist(tr.MAE.values, bins=30); ax[1].set_title("MAE (R)")
    fig.tight_layout(); fig.savefig(ROOT/f"reports/mfe_mae_{tf}_{split}.png", dpi=100); plt.close(fig)
print("plots done")
