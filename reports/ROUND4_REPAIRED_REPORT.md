# ROUND4_REPAIRED_REPORT.md — Infrastructure repair, no new hypotheses

## 1. Round 4 audit: p_prereg = 0.5 verdict: PLACEHOLDER, NOT a result
- `research/run_round4.py` lines ~117–126: permutation block generated `rng.normal(0,0.1)` noise into unused
  `diffs`, hardcoded `p=0.5` (or 1.0 when n<30). FAMILY p-values fed to BH-FDR were constants.
- Official finding: original Round 4 FDR conclusions are **INVALID / INCOMPLETE**. Historical file
  `reports/round4.json` preserved unmodified; do not cite its q-values. Directional expectancies in that file
  were computed from real trades and are retained as descriptive only.

## 2. Macro data audit (daily, Yahoo, UTC, no NaNs)
| key | ticker | real/proxy | rows | coverage | tz | missing |
| DXY | DX-Y.NYB | real index | 14152 | 1971→2026 | UTC | 0 |
| Y10 | ^TNX | real 10Y | 16172 | 1962→2026 | UTC | 0 |
| YSHORT | ^IRX | PROXY (13wk, not 2Y) | 16669 | 1960→2026 | UTC | 0 |
| VIX | ^VIX | real | 9254 | 1990→2026 | UTC | 0 |
| SPX | ^GSPC | real (NASDAQ: DATA GAP) | 24802 | 1927→2026 | UTC | 0 |
| OIL | CL=F | real front-month | 6552 | 2000→2026 | UTC | 0 |
| TIP | TIP | PROXY (ETF price, not real yield) | 5738 | 2003→2026 | UTC | 0 |
- TIP ≠ real yield. ^IRX ≠ 2Y. Never treated as exact equivalence.

## 3. Hourly dataset (Yahoo 2y cap; spot research window 2020–22 has NO hourly macro)
Saved separately under `data/raw/MACRO_*_H1_yahoo.csv`, never forward-filled:
| key | rows | span | missing vs 24/7 grid |
| DXY | 11934 | 2024-09→2026-09 | 31.8% (weekends/closures) |
| Y10 | 3500 | 2024-09→2026-09 | 80.0% (bond hours only) |
| VIX | 7109 | 2024-09→2026-09 | 59.3% (US hours) |
| SPX | 3480 | 2024-09→2026-09 | 80.1% (US hours) |
| OIL | 11279 | 2024-09→2026-09 | 35.5% |
- Stale/closure bars documented by absence (no imputation). Timezone normalized to UTC on load.

## 4. Macro event data: DATA NOT AVAILABLE
No reliable free historical CPI/NFP/FOMC/PCE timestamp feed exists in this environment (FRED needs a key;
calendar scraping is unverifiable). Not fabricated. Windows untested.

## 5. Causal alignment: VERIFIED
- Macro merged by calendar date then shifted one full day (`cal_shift`), so every H1 bar uses only
  previously closed daily data: feature_timestamp < decision_timestamp always.
- No revised values (vintages unavailable — documented limitation favoring null, not edge).
- Reproduction detect() verified bar-for-bar: research n_base breakout_up 1037, sweep_high 634,
  failed_breakout 840 — identical to original Round 4 counts.

## 6. Rebuilt statistics + unit tests (6 passed)
- `statsx/permutation.py`: real permutation p on observed trade-R vectors, real bootstrap CI, real BH-FDR.
- `tests/test_stats.py`: fails on constant p-values (separated-vs-identical groups, family variance, FDR monotonicity).

## 7. Reproduction (EXACT 12 hypotheses, thresholds/splits unchanged)
Real permutation p (research): min 0.074 (sweep_high×DXY_ret1=+1, negative direction); BH q min 0.89.
Validation: all null/negative; VIX-hi and failed×any cells n=0 (INSUFFICIENT DATA, incl. one vacuous
filter misspecification carried over verbatim and labeled, not silently dropped).
Official result: corrected Round 4 still shows NO validated edge. Same verdict, now on valid statistics.

## 8. Data-quality gate
- [x] no placeholder p-values (replaced + tested)
- [x] causal timestamps verified (prev-day shift; count-identical reproduction)
- [x] macro alignment verified
- [x] missing data documented (hourly grid gaps; H1-macro 2020–22 gap)
- [x] proxies explicitly labeled (IRX, TIP, NASDAQ gap, event-feed gap)
- [x] FDR implementation tested (6/6 pytest)
- [x] Round 4 reproduced (exact counts)
- [x] validation split unchanged (2023; final 2024–26 never loaded by R4 code)
- [x] final OOS remains locked
GATE: PASS. Round 5 may be proposed. Improved nothing about profitability — repair only.
