# PREREGISTRATION — R6 ROUND 3 (VWAP/EMA reversion probes + rejection filter info)
Status: PREREGISTERED. Rounds 1–2 frozen (0/48). Final OOS 2024+ LOCKED. No Fibonacci, no ML, no indicator grid search.

## D1 — intraday VWAP/EMA mean-reversion probes (descriptive first)
- Anchors: session VWAP (UTC day, typical-price × M1 tick_volume; reset daily) and EMA20 on M5 close.
- Deviation z = (close − anchor)/ATR14, evaluated at M5 close, Mon–Fri 07–19h UTC.
- Buckets (fixed): |z| in [0.5,1) / [1,1.5) / [1.5,2) / [2,∞), side above/below → 8 cells per anchor, 16 total.
- Per cell: n, P(return halfway to anchor within next 12 M5 bars), MFE/MAE in ATR units, standardized fade-probe expectancy after costs (SL1×ATR, TP1×ATR, 12-bar, flat 21UTC, 1x/2x costs). NOT a strategy.
- Family: 16 cells, BH-FDR. Promotion: validation net>0 AND ≥2/3 WF AND 2x>0 AND beats matched random AND n≥100.

## D2 — PDH/PDL rejection + single-filter incremental info (no combos)
- Base: first-of-day rejection (M5 wick pierces PDH/PDL, close back inside), fade direction, SL1/TP1/12b, 07–19h.
- Filters (each tested ALONE vs base, fixed splits):
  F1 magnitude: wick > 0.5 ATR vs ≤ 0.5
  F2 vol regime: LOW / NORM / HIGH (M5 RV48 trailing-1000 quantile, fixed thirds)
  F3 distance from daily open: > 1.0 ATR vs ≤ 1.0
  F4 session: LONDON / OVERLAP / NY (descriptive split, no pooling)
  F5 reclaim speed: back inside in 1 bar vs 2–3 bars
  F6 rejection-bar body/range: > 0.5 vs ≤ 0.5
- Per sub-cell: net expectancy after costs + bootstrap CI; contrast vs base via permutation (Δmean); BH-FDR across the 13 sub-cells (base excluded from family, reported).
- "Incremental information" = sub-cell net significantly different from base AND economically same-or-better after 2x costs. No combinations in Round 3.

## D3 — News
No timestamped CPI/NFP/FOMC feed exists in this pipeline (DATA GAP logged since R4; verified 2026-09-29: no news/calendar files). Direction CLOSED without testing. If a free timestamped calendar appears later, it needs its own preregistration.

## Promotion bar (any D1/D2 cell)
Validation net>0 AND ≥2/3 WF positive AND 2x costs>0 AND beats matched random AND n≥100 AND no parameter cliff AND no leakage. Else STOP RESEARCH and record: no statistically robust edge found in this XAUUSD intraday pipeline.
