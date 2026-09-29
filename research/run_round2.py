"""R6 ROUND 2 STAGE 1 — first-touch breakout + sweep-reclaim (prereg PREREG_R6_ROUND2.md).
Research 2020-22 -> validation 2023. 2024+ NEVER read. Round 1 frozen, not retested.
Stage-1 exec (fixed): SL1.0/TP1.0/12-bar, flat 21:00 UTC, costs 1x/2x/3x."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research import run_intraday_r6 as R6
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment

SESSIONS = {"LONDON": (7.0, 12.0), "OVERLAP": (12.0, 14.0), "NY": (14.0, 17.0)}
CELLS = [f"{f}_{s}" for f in ["FTBO", "SWEEP"] for s in SESSIONS]
EXEC = dict(sl_atr=1.0, tp_r=1.0, max_hold=12, flat_hour=21)


def detect_stage1(m5):
    """6 cells. Levels pooled (PDH/PDL/AH/AL); split per level only in Stage 3."""
    ev = {}
    ok = m5.atr14.notna() & (m5.atr14 > 0) & m5.PDH.notna() & m5.AH.notna()
    base = m5[ok].copy()
    hr = base.timestamp.dt.hour + base.timestamp.dt.minute / 60
    th = 0.1 * base.atr14
    lv = {"PDH": (base.PDH, 1), "PDL": (base.PDL, -1),
          "AH": (base.AH, 1), "AL": (base.AL, -1)}
    for sess, (lo, hi) in SESSIONS.items():
        in_s = (hr >= lo) & (hr < hi)
        # FTBO: first close beyond level+0.1ATR per (date, level) inside session
        ft = []
        for name, (col, direction) in lv.items():
            if direction == 1:
                t = base[in_s & (base.close > col + th)]
            else:
                t = base[in_s & (base.close < col - th)]
            t = t.groupby("date").head(1)
            ft.append(t.assign(direction=direction)[["timestamp", "direction"]])
        ev[f"FTBO_{sess}"] = pd.concat(ft).sort_values("timestamp").reset_index(drop=True)
        # SWEEP_RECLAIM (N=3): support PDL/AL low<lvl then close>lvl -> long;
        # resistance PDH/AH high>lvl then close<lvl -> short; reclaim inside session
        sw = []
        for name, (col, direction) in lv.items():
            if direction == 1:  # resistance: sweep up, reclaim down -> short
                swept = base.high > col
                back = base.close < col
                d = -1
            else:               # support: sweep down, reclaim up -> long
                swept = base.low < col
                back = base.close > col
                d = 1
            # reclaim within 3 bars of a sweep bar (causal rolling window)
            sw_any = swept.rolling(3, min_periods=1).max().astype(bool)
            rec = base[in_s & back & sw_any]
            # keep first reclaim per (date, level)
            rec = rec.groupby("date").head(1)
            sw.append(rec.assign(direction=d)[["timestamp", "direction"]])
        ev[f"SWEEP_{sess}"] = pd.concat(sw).sort_values("timestamp").reset_index(drop=True)
    return ev


def evaluate(m5, sp5, fall):
    ev = detect_stage1(m5)
    out, P, Rs = {}, [], {}
    for cell in CELLS:
        sess = cell.split("_", 1)[1]
        lo, hi = SESSIONS[sess]
        r1 = R6.backtest(m5, ev[cell], sp5, fall, 1.0, entry_lo=lo, entry_hi=19.0, **EXEC)
        st = R6.stats(r1)
        e2 = float(np.nanmean(R6.backtest(m5, ev[cell], sp5, fall, 2.0, entry_lo=lo, entry_hi=19.0, **EXEC))) if len(r1) else None
        e3 = float(np.nanmean(R6.backtest(m5, ev[cell], sp5, fall, 3.0, entry_lo=lo, entry_hi=19.0, **EXEC))) if len(r1) else None
        st["exp_R_2x"] = round(e2, 4) if e2 is not None and np.isfinite(e2) else None
        st["exp_R_3x"] = round(e3, 4) if e3 is not None and np.isfinite(e3) else None
        # matched random: same session pool, same n, identical exec
        rng = np.random.default_rng(1000 + CELLS.index(cell))
        pool = m5[(m5.timestamp.dt.hour + m5.timestamp.dt.minute / 60 >= lo) &
                  (m5.timestamp.dt.hour + m5.timestamp.dt.minute / 60 < hi)].index.values
        n = len(r1)
        rr = np.array([])
        if n and len(pool):
            ri = rng.choice(pool, size=min(n, len(pool)), replace=False)
            rsig = pd.DataFrame({"timestamp": m5.timestamp.iloc[ri].reset_index(drop=True),
                                 "direction": rng.choice([-1, 1], size=len(ri))})
            rr = R6.backtest(m5, rsig, sp5, fall, 1.0, entry_lo=lo, entry_hi=19.0, **EXEC)
        st["random_n"] = int(len(rr))
        st["random_exp_R"] = round(float(np.nanmean(rr)), 4) if len(rr) else None
        a = r1[np.isfinite(r1)]; b = rr[np.isfinite(rr)]
        if len(a) >= 100 and len(b) >= 30:
            p, diff = permutation_diff_p(a, b)
        else:
            p, diff = 1.0, 0.0
        st["perm_p_vs_random"] = round(float(p), 4)
        st["diff_vs_random"] = round(float(diff), 4)
        out[cell] = st
        P.append(float(p) if st["n"] >= 100 else 1.0)
    q = bh_fdr_real(P)
    for k, qq in zip(CELLS, q):
        out[k]["q"] = round(float(qq), 4)
    return out


def main():
    out = {"prereg": "R6-round2-stage1; FTBO+sweep x LN/OV/NY; SL1/TP1/12b",
           "research": {}, "validation": {}, "walkforward": {}}
    m5r, sp5r, fallr = R6.run_split("research_data", [2020, 2021, 2022])
    out["research"] = evaluate(m5r, sp5r, fallr)
    print("research done", flush=True)
    m5v, sp5v, fallv = R6.run_split("validation_data", [2023])
    out["validation"] = evaluate(m5v, sp5v, fallv)
    print("validation done", flush=True)
    m1all = pd.concat([R6.load_m1("research_data"), R6.load_m1("validation_data")]).sort_values("timestamp")
    yrs = m1all.timestamp.dt.year.values
    for tr, te in [([2020], [2021]), ([2020, 2021], [2022]), ([2020, 2021, 2022], [2023])]:
        sub = m1all[np.isin(yrs, te)].reset_index(drop=True)
        m5t = R6.build_m5(sub)
        sp = R6.load_spread_m5(te)
        f = float(sp.spread.mean()) if sp is not None else 0.35
        ev = detect_stage1(m5t)
        wf = {}
        for cell in CELLS:
            sess = cell.split("_", 1)[1]
            lo, _hi = SESSIONS[sess]
            r = R6.backtest(m5t, ev[cell], sp, f, 1.0, entry_lo=lo, entry_hi=19.0, **EXEC)
            st = R6.stats(r)
            wf[cell] = {"n": st.get("n", 0), "exp_R": st.get("exp_R"), "ci95": st.get("ci95")}
        out["walkforward"][f"{tr}->{te}"] = wf
    print("walkforward done", flush=True)
    with open(ROOT/"reports"/"round2_stage1.json", "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    log_experiment({"hypothesis": "R6 round2 stage1 FTBO/sweep", "dataset": "research 2020-22 -> validation 2023",
                    "results": {"cells": CELLS}, "status": "REJECTED"})
    for split in ["research", "validation"]:
        print(f"== {split} ==", flush=True)
        for c in CELLS:
            s = out[split][c]
            print(f"{c:14s} n={s.get('n')} exp={s.get('exp_R')} ci={s.get('ci95')} "
                  f"2x/3x={s.get('exp_R_2x')}/{s.get('exp_R_3x')} "
                  f"rnd={s.get('random_n')}/{s.get('random_exp_R')} "
                  f"p={s.get('perm_p_vs_random')} q={s.get('q')}", flush=True)
    return out


if __name__ == "__main__":
    main()
