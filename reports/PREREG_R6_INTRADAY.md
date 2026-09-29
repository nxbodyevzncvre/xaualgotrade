# PREREGISTRATION — R6 INTRADAY XAUUSD (Round 1: structure, not optimization)

Status: PREREGISTERED. Final OOS (final_test_data/, 2024-01 → 2026-09) LOCKED — never read, never listed beyond lock confirmation.

## Firewall
- Research: 2020–2022 — research_data/XAUUSD_M1_duk.csv (bid) + data/raw/_tickagg/min_2020*.csv..min_2022*.csv (bid/ask)
- Validation: 2023 — validation_data/XAUUSD_M1_duk.csv + min_2023*.csv
- Final OOS: 2024+ — LOCKED. No reads, no stats, no plots.

## Day-trade execution (FIXED for all Round-1 events, not tuned)
- Grid: M5 (Dukascopy spot bid). Signal at M5 close, entry next executable M5 close.
- Entry window: Mon–Fri, 07:00–19:00 UTC. Hard flat: 21:00 UTC same day (close at bid, cost applied). No overnight/weekend.
- SL 1.5×ATR14 (M5 true-range), TP 2R, time stop 24 M5 bars (2h). Ambiguous same-bar SL/TP → SL (conservative).
- Costs: per-trade spread = (spread_entry_bar + spread_exit_bar)/2 from tick minute means merged to M5 (fallback: period mean); slippage 0.15 USD. Sweeps: 1x / 2x / 3x total cost. 1x gate is necessary, not sufficient (fragile if only 1x passes).
- ATR/vol/sessions recomputed causally (rolling/min_periods, no future).

## Sessions (R6 bins, UTC, fixed)
asian 00–07, london 07–12, overlap 12–14, ny 14–17, off otherwise.

## Round-1 event family (FIXED definitions, 10 cells + random baseline)
1. ASIAN_BO: Asian range (00–07 high/low). First M5 close beyond range ± 0.1×ATR after 07:00 → breakout direction.
2. ASIAN_FADE: first touch of Asian high/low after 07:00 with close back inside range → fade (toward range mid).
3. PDH_BO / PDL_BO: close beyond prev-day high/low + 0.1×ATR (07–19h) → breakout direction.
4. PDH_REJ / PDL_REJ: M5 high/low pierces PDH/PDL but close back inside → fade.
5. SESSION_MOMO_london / _overlap / _ny: M5 close in top/bottom tercile of prior-12-bar return distribution during that session → continuation (momentum probe, fixed lookback 12).
6. RANDOM: random direction at random 07–19h M5 bars, same exec/costs, n matched to median event n. The bar every event must clear.

PDH/PDL/PDC from UTC-day M1 bars (causal: prior completed day only).

## Statistics (fixed)
- Per cell: n, expectancy R + bootstrap 95% CI (B=2000, seed 0), win rate, PF, median, maxDD (fixed 1R sizing), cost-sweep expectancy (1x/2x/3x).
- Baseline contrast: permutation_diff_p(event R vs RANDOM R, B=2000, seed 0).
- BH-FDR across the 10 event cells (RANDOM excluded from family; reported separately).
- Walk-forward (recorded, same exec): train 2020→test 2021; train 2020–21→test 2022; train 2020–22→test 2023.
- min_n = 100 for any claim; cells below reported descriptively.
- Promotion bar (Round 2): validation expectancy CI excludes 0 AND q<0.10 AND 1x/2x/3x all >0 AND walk-forward ≥2/3 positive. Otherwise STOP/REJECT.

## Forbidden in Round 1
SL/TP/hold/threshold/session/level re-tuning on results; new events post-hoc; strategy assembly; any 2024+ access; ML.
Fibonacci, news, ML explicitly OUT of Round 1 (priority order §30: sessions/levels first).
