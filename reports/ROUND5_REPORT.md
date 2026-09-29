# ROUND5_REPORT.md — XAUUSD Intraday Microstructure (prereg R5-001)
M1 primary (Dukascopy spot bid, native, never resampled), native M5 robustness.
Final 2024→2026 LOCKED, never touched. No strategy built.

## 1. Data verification
- M1 2,390,052 bars / M5 478,140, 2020-01-01→2026-09-28, 0 dups, 0 impossible OHLC.
- Splits: research 2020→2022-12-30 (1,064,466 M1), validation 2023 (352,949), final locked (972,637).
- Decisions on M5 grid (~210k research / ~70k validation). R-targets: systematic every-6th decision.

## 2. Session filter (R5-SESSION-001, unoptimized, identical all splits)
Keep Mon–Fri UTC (`weekday < 5`); Sat/Sun quote artifacts excluded from research only. Raw immutable.

## 3. Leakage tests (10/10 pytest incl. prior suites)
m5_frame/order/efficiency recomputation-identity; F2 formation causality (added after catching a real
leak: ATR-at-hour-end inflated F2 hits — fixed, hits vanished). Two further bugs caught and fixed with
disclosure: tz-stripping `.values` join (F8 empty frame), R-loop stale entry (see 11).

## 4–5. Hypotheses (34 research tests, order §18) and predictive distributions
- F1 path×close-loc (6): research q<0.05 for 2; VALIDATION FAILED (q 0.26–0.91, signs vanish).
- F2 formation (3): rejected after leakage fix. Documented as a catch, not a result.
- F3 H/L order (4): research q≤0.03 (HF→+0.0086, 3-bar +0.026 ATR); VALIDATION FAILED (all q>0.59, effects →0).
- F4 vol states (4): REPLICATED (LOW/NORM/HIGH |return| diffs, q≤0.09) — volatility clustering, expected.
- F5 sequences (9): REPLICATED (1-bar reversal P_up 0.485/0.512; 2-bar same pattern; q≤0.02, same signs, smaller magnitude).
- F6 efficiency (5): directional hi q=0.09→validation FAIL (q=0.35); |return| magnitude (hi_abs) REPLICATED both sides.
- F7 HF×session (4): research off-hours hit; VALIDATION FAILED (q=0.34).
- Conditional-vs-unconditional distributions archived in round5_research.json / round5_validation.json.

## 6. Sample sizes: 15k–106k per test (research), 8k–35k (validation). Power is high — significance is cheap.

## 7. Effect sizes (the gate that matters)
- Directional survivors: ±0.012–0.027 in P(up next M5); mean next-M5 ±0.005 ATR ≈ $0.005.
  Median M5 ATR = $0.992; spread alone $0.35 = 0.35 ATR — the effect is ~70× smaller than spread.
- F8: C−A AUC +0.010, CI95 [0.008, 0.012] — significant, negligible.
- M5-native analogues F3m/F6m/F1m: all null (p 0.12–0.62).

## 8. Permutation tests: within-sample label shuffle (B=2000); research 34 p-values, BH-FDR; validation
19 retests with fresh FDR (min q for failures 0.23–0.91).

## 9. FDR: research qmin 0.001 (19 survivors at q<0.10); validation: 9 survive (F4×3, F5×6... F5_2_UPUP q=0.020,
F6-abs×2), 10 rejected (all directional path/order/efficiency claims).

## 10. Validation summary: direction fails; magnitude/reversal-rate replicate.
F4/F5-rate/F6-abs replicate sign and rough magnitude. F1/F3/F6-dir/F7 do not.

## 11. M1 vs M5 robustness: M1-only directional claims have no M5 analogue signal; F5/F4/F6-abs are
M5-frame-native and replicate. R-race (fixed entries, 1-min implementation lag disclosed, ambiguity-as-loss,
RAND control 0.511): F3 0.50/0.49, F5 0.51/0.50 — indistinguishable from chance. The 0.75 in the first
R run was a stale-entry artifact (entry inside signal window), discarded, documented.

## 12. H1 vs H1+M5 vs H1+M5+M1 (validation, next-M5 up): A 0.6000 / B 0.6051 / C 0.6103.
M1 path adds +0.010 AUC over H1 (CI excludes 0, economically negligible). Brier/logloss differences ≤0.003.

## 13. Rejected: F1, F2, F3, F6-directional, F7, F1m/F3m/F6m analogues, any spread-adjusted edge (P≈RAND).

## 14. Surviving (narrowly defined): short-horizon return reversal rates (F5), volatility-state magnitude
(F4), efficiency-magnitude (F6-abs). All are microstructure regularities with NO demonstrated tradability.

## FINAL QUESTION
M1 path provides statistically significant incremental information over H1 (ΔAUC +0.010, reversal-rate
shifts ±2pp, all replicated). Magnitude: ~$0.005–0.03 per event vs $0.50 round-trip cost assumption.
There is predictive information; there is no exploitable edge in this dataset. NO ROUND 6. STOP.
