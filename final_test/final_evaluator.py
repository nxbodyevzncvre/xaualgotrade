"""FINAL evaluator: reads frozen strategy + final data ONLY. One-way report, no feedback."""
import json, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backtesting.engine import backtest_signals
from statsx.tests import expectancy, trade_stats

def run(freeze_path: str, final_csv: str, out_path: str):
    with open(freeze_path) as f:
        fr = json.load(f)
    df = pd.read_csv(final_csv, parse_dates=["timestamp"])
    # rebuild signals per frozen rule (only fib+structure+vol rule supported in Phase 1)
    import features.swings as SW, features.fibonacci as FIB, features.volatility as V, features.structure as ST
    p = fr["parameters"]
    df = V.add_volatility(df, p.get("atr_period", 14))
    sw = SW.fractal_swings(df, p.get("fractal_k", 2))
    df = ST.add_structure(df, sw)
    pairs = FIB.pairs_to_retracements(sw)
    sigs = []
    for _, r in pairs.iterrows():
        c0 = int(r.confirm_idx)
        if c0 >= len(df):
            continue
        if p.get("use_trend_filter") and df.trend_state.iloc[c0] == 0:
            continue
        if p.get("use_vol_filter"):
            if df.vol_regime.iloc[c0] != p.get("vol_regime", "mid"):
                continue
        lvl = p.get("fib_level", 0.618)
        lp = FIB.level_price(r.lo, r.hi, lvl, r.direction)
        a = df.atr.iloc[c0]
        d = 1 if df.close.iloc[c0] < lp else -1
        # mean-reversion toward swing extreme: fade the level
        sigs.append({"idx": c0+1, "direction": -d if p.get("fade_level", True) else d})
    sigs = pd.DataFrame(sigs)
    tr = backtest_signals(df, sigs, p.get("sl_atr", 1.5), p.get("tp_R", 2.0),
                          p.get("max_hold", 20), fr["costs"]["spread"], fr["costs"]["slippage"])
    rep = {"strategy": fr["strategy_id"], "n_trades": len(tr),
           "expectancy": expectancy(tr.R.values) if len(tr) else {},
           "stats": trade_stats(tr.R.values) if len(tr) else {},
           "note": "FINAL OOS. Do not use to modify strategy."}
    with open(out_path, "w") as f:
        json.dump(rep, f, indent=2)
    print(json.dumps(rep, indent=2))

if __name__ == "__main__":
    run(sys.argv[1], sys.argv[2], sys.argv[3])
