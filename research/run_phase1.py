"""Phase 1: EXP-01..05 on RESEARCH data only. Final test never touched."""
import json, sys
from pathlib import Path
import pandas as pd
import numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, fibonacci as FIB, volatility as V, structure as ST
from backtesting.engine import backtest_signals
from statsx.tests import prop_test, bootstrap_ci, bh_fdr, expectancy, trade_stats
from research.registry import log_experiment
from validation.splits import walkforward_windows

CFG = json.load(open(ROOT / "configs" / "config.json"))
COST = CFG["costs"]

def load(sym, tf, split):
    p = ROOT / split / f"{sym}_{tf}.csv"
    df = pd.read_csv(p, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    return V.add_volatility(df)

def fib_signals(df, pairs, level=0.618, fade=True, trend_filter=False, vol_filter=None):
    sigs = []
    for _, r in pairs.iterrows():
        c0 = int(r.confirm_idx)
        if c0 + 1 >= len(df):
            continue
        if trend_filter and df.trend_state.iloc[c0] == 0:
            continue
        if vol_filter and df.vol_regime.iloc[c0] != vol_filter:
            continue
        lp = FIB.level_price(r.lo, r.hi, level, r.direction)
        base = df.close.iloc[c0]
        d = 1 if base < lp else -1
        sigs.append({"idx": c0+1, "direction": -d if fade else d})
    return pd.DataFrame(sigs)

def run():
    report = {"decisions": "autonomous defaults per config.json", "exps": {}}
    for tf in ["D1", "H1"]:
        df = load("XAUUSD", tf, "research_data")
        sw = SW.fractal_swings(df, CFG["swing"]["fractal_k"])
        df = ST.add_structure(df, sw)
        pairs = FIB.pairs_to_retracements(sw)
        react = FIB.measure_reactions(df, pairs, CFG["fib_levels"])
        # EXP-01: fib touched-reaction vs random touched-reaction
        fib = react[react.kind == "fib"]
        rnd = react[react.kind == "random"]
        ft = fib[fib.touched]; rt = rnd[rnd.touched]
        t1 = prop_test(int(ft.reacted.sum()), len(ft), int(rt.reacted.sum()), len(rt))
        # per-level detail
        per_level = []
        pvals = []
        for lvl in CFG["fib_levels"]:
            s = fib[(fib.level == lvl) & (fib.touched)]
            t = prop_test(int(s.reacted.sum()), len(s), int(rt.reacted.sum()), len(rt))
            pvals.append(t["p"])
            per_level.append({"level": lvl, "n": len(s), "rate": float(s.reacted.mean()) if len(s) else 0.0, **t})
        qvals = bh_fdr(pvals)
        for d, q in zip(per_level, qvals):
            d["q_fdr"] = float(q)
        e1 = {"tf": tf, "n_pairs": len(pairs), "fib_touched": len(ft),
              "fib_rate": float(ft.reacted.mean()) if len(ft) else 0.0,
              "rand_touched": len(rt), "rand_rate": float(rt.reacted.mean()) if len(rt) else 0.0,
              "test": t1, "per_level": per_level}
        log_experiment({"hypothesis": "H1 fib reaction != random", "dataset": f"research XAUUSD {tf}",
                        "features": "fractal swings + retracements", "parameters": CFG["reaction"],
                        "results": e1, "status": "PROMISING" if t1["p"] < 0.05 else "REJECTED"})
        report["exps"][f"EXP01_{tf}"] = e1
        # EXP-02: 61.8 vs pooled others
        s61 = fib[(fib.level == 0.618) & (fib.touched)]
        soth = fib[(fib.level != 0.618) & (fib.touched)]
        t2 = prop_test(int(s61.reacted.sum()), len(s61), int(soth.reacted.sum()), len(soth))
        e2 = {"n61": len(s61), "rate61": float(s61.reacted.mean()) if len(s61) else 0.0,
              "n_other": len(soth), "rate_other": float(soth.reacted.mean()) if len(soth) else 0.0, "test": t2}
        log_experiment({"hypothesis": "H2 61.8 special vs other fibs", "dataset": f"research XAUUSD {tf}",
                        "results": e2, "status": "PROMISING" if t2["p"] < 0.05 else "REJECTED"})
        report["exps"][f"EXP02_{tf}"] = e2
        # EXP-03 / EXP-04: strategy-level backtests in R
        for lvl in [0.5, 0.618]:
            base_sig = fib_signals(df, pairs, lvl)
            tr_base = backtest_signals(df, base_sig, CFG["risk"]["sl_atr"], CFG["risk"]["tp_R"],
                                       CFG["risk"]["max_hold_bars"], COST["spread_xauusd"], COST["slippage"])
            eb = expectancy(tr_base.R.values) if len(tr_base) else {"exp_R": 0.0, "n": 0}
            trend_sig = fib_signals(df, pairs, lvl, trend_filter=True)
            tr_t = backtest_signals(df, trend_sig, CFG["risk"]["sl_atr"], CFG["risk"]["tp_R"],
                                    CFG["risk"]["max_hold_bars"], COST["spread_xauusd"], COST["slippage"])
            et = expectancy(tr_t.R.values) if len(tr_t) else {"exp_R": 0.0, "n": 0}
            report["exps"][f"EXP03_{tf}_lvl{lvl}"] = {"base": eb, "trend_filtered": et,
                "base_stats": trade_stats(tr_base.R.values) if len(tr_base) else {},
                "trend_stats": trade_stats(tr_t.R.values) if len(tr_t) else {}}
            log_experiment({"hypothesis": "H3/H4 fib+structure vs fib alone", "dataset": f"research XAUUSD {tf} lvl={lvl}",
                            "results": report["exps"][f"EXP03_{tf}_lvl{lvl}"], "status": "PROMISING" if et.get("exp_R", 0) > eb.get("exp_R", 0) else "REJECTED"})
            for regime in ["low", "mid", "high"]:
                vs = fib_signals(df, pairs, lvl, vol_filter=regime)
                tr_v = backtest_signals(df, vs, CFG["risk"]["sl_atr"], CFG["risk"]["tp_R"],
                                        CFG["risk"]["max_hold_bars"], COST["spread_xauusd"], COST["slippage"])
                report["exps"][f"EXP04_{tf}_lvl{lvl}_{regime}"] = expectancy(tr_v.R.values) if len(tr_v) else {"exp_R": 0.0, "n": 0}
        # EXP-05 walk-forward on research slice
        wf = []
        for tr_df, te_df in walkforward_windows(df, 3):
            sw_tr = SW.fractal_swings(tr_df, CFG["swing"]["fractal_k"])
            tr_df2 = ST.add_structure(V.add_volatility(tr_df) if "atr" not in tr_df else tr_df, sw_tr)
            pairs_te = FIB.pairs_to_retracements(SW.fractal_swings(te_df, CFG["swing"]["fractal_k"]))
            te_df2 = ST.add_structure(te_df, SW.fractal_swings(te_df, CFG["swing"]["fractal_k"]))
            sig = fib_signals(te_df2, pairs_te, 0.618, trend_filter=True)
            trd = backtest_signals(te_df2, sig, CFG["risk"]["sl_atr"], CFG["risk"]["tp_R"],
                                   CFG["risk"]["max_hold_bars"], COST["spread_xauusd"], COST["slippage"])
            wf.append(expectancy(trd.R.values) if len(trd) else {"exp_R": 0.0, "n": 0})
        report["exps"][f"EXP05_{tf}"] = wf
        log_experiment({"hypothesis": "H5 walk-forward persistence", "dataset": f"research XAUUSD {tf}",
                        "results": wf, "status": "VALIDATED" if sum(1 for w in wf if w.get("exp_R", 0) > 0) >= 2 else "REJECTED"})
    with open(ROOT / "reports" / "phase1_report.json", "w") as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    run()
