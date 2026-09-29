# PREREGISTRATION — R6 ROUND 2 (Stage 1: first-touch + sweep-reclaim, short execution)
Status: PREREGISTERED. Round 1 frozen (0/30). Final OOS 2024+ LOCKED — never read.
EXP-000106 stays PHENOMENON ONLY, not used as a feature here.

## Question
Was Round-1 failure caused by the every-bar/2R/24-bar execution model rather than
absence of all intraday directional structure? No cosmetic retests of Round 1.

## Stage-1 matrix (6 cells, fixed before execution)
Families × sessions:
- FIRST_TOUCH_BREAKOUT × {LONDON 07–12, OVERLAP 12–14, NY 14–17} (UTC, Mon–Fri)
- SWEEP_RECLAIM × {LONDON, OVERLAP, NY}
Levels pooled in Stage 1: PDH / PDL / ASIAN_HIGH / ASIAN_LOW (split per level only in Stage 3 for promoted families).

## Event definitions (causal, one signal per level per day max)
- FIRST_TOUCH_BREAKOUT: first M5 close beyond level + 0.1×ATR14 (PDH/AH → LONG; PDL/AL → SHORT) with timestamp inside the evaluated session. Later touches same day ignored.
- SWEEP_RECLAIM (N=3 bars, fixed): support levels (PDL/AL): M5 low < level AND close back above level within 3 bars → LONG at reclaim close. Resistance (PDH/AH): M5 high > level AND close back below within 3 bars → SHORT. Sweep bar itself must be inside-or-before the session; reclaim close inside evaluated session.
- Asian range = same-date 00–07 UTC high/low (known from 07:00). PDH/PDL = prior completed UTC day.

## Execution (Stage 1, fixed)
SL 1.0×ATR14, TP 1.0R, time stop 12 M5 bars. Entry = open of bar after signal. Hard flat 21:00 UTC. Entry window = evaluated session hours only.
Costs: per-trade spread (tick M5 mean, fallback period mean) + 0.15 slippage; sweeps 1x/2x/3x.

## Baselines / stats
- Matched RANDOM per cell: same session pool, same n, random direction, identical exec/costs.
- Per cell: n, gross/net expectancy + bootstrap CI (B=2000 seed 0), PF, maxDD, cost sweeps, permutation vs matched random, BH-FDR across the 6 cells. min_n=100.
- Walk-forward: 2020→21, 2020–21→22, 2020–22→23 (same exec).
- Promotion (Stage 2): validation exp>0 AND ≥2/3 WF positive AND beats random AND 2x costs>0 AND n≥100 AND no single-window catastrophic DD. Else STOP/REJECT. No strategy assembly. No 2024+.
