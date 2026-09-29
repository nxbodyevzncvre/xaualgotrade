# XAUUSD Fibonacci Research — Final Report (Phase 1, autonomous defaults)

## EXECUTIVE SUMMARY
- Verdict: **NOT SUPPORTED** (H1/H2/H7/H8/H9/H10), **INSUFFICIENT EVIDENCE** at best for one H3/H4 sub-variant (H1 50% + high-vol).
- EXP-01 (reaction vs random): D1 p=0.39, H1 p=0.33. Fib rate slightly *below* random. FDR q>0.5 all levels.
- EXP-02 (61.8 special): D1 p=0.94, H1 p=0.89. No distinction.
- EXP-03/04: only H1 50% + high-ATR regime nominally positive on research (+0.14R CI [0.04,0.24] n=524); validation +0.22R CI [-0.05,0.47] n=93; **final OOS (locked, single run) -0.17R CI [-0.37,+0.05] n=104**. Failed blind test.
- D1 validation negative; walk-forward D1 0/3 positive, H1 3/3 nominally positive but CIs cross 0.
- No systematic strategy justified. Do not trade this.

## HYPOTHESIS
H1 reaction non-random; H2 61.8 predictive; H3 geometry+vol; H4 fib+structure beyond indicators;
H5 OOS survival; H6 costs; H7 param stability; H8 regime stability; H9 period stability; H10 systematic justification.
Classifications per section 31 only.

## DATA
- Source: Yahoo `GC=F` proxy (MT5 Python API unavailable on macOS). Raw in `data/raw/`, meta in `data/metadata/`.
- D1: 6544 bars 2000-08-30→2026-09-28. H1: 11461 bars 2024-09-29→2026-09-28 (Yahoo 2y cap). H4 resampled 3102 bars.
- Splits: D1 date-based (research <2023: 5604; validation 2023: 251; final ≥2024: 689). H1 70/15/15 chronological (8022/1719/1720).
- Costs: spread 0.35 + slippage 0.15 (conservative XAUUSD); sweeps 1×/2×/3×.
- Limitation: GC=F futures proxy ≠ spot XAUUSD; no tick spread/volume; H1 history short (2y); Yahoo rate limits.

## METHODOLOGY
- Causal swings only (fractal k=2 confirm=i+k; ATR-pivot; ZigZag). Signal timestamp = confirmation bar.
- Retracement grid from consecutive alternating swings; levels 23.6/38.2/50/61.8/78.6 + random U(0.1,0.9) control per pair.
- Reaction: touch within ±0.25 ATR (or overlap) in next 10 bars + 0.25 ATR reversal. Fixed-R backtest: entry next close, SL 1.5 ATR, TP 2R, 20-bar stop, ambiguous bar → SL.
- Stats: two-proportion z, bootstrap 95% CI (2000), BH-FDR, expectancy/R, walk-forward (3 windows), MC bootstrap, heatmaps.

## DATA QUALITY
- Duplicates 0, impossible OHLC 0, missing 0. Gaps >3×median: D1/H1/H4 present (weekends/closures). Weekend bars exist in Yahoo (filtered by analysis implicitly via ATR NaN drop). Extreme >5% moves: 1. No silent repair.

## EXPERIMENT REGISTRY
- `research/experiments/registry.jsonl` append-only (EXP-000001…). Statuses used: REJECTED/PROMISING/VALIDATED. No deletions.

## BASELINES
- H1 validation random entry (n=496): +0.025R CI [-0.08,+0.14]. Candidate +0.22R vs random +0.02R — difference inside noise. D1 random +0.026R vs candidates negative. SMA/ATR-breakout/buy-hold not run beyond random — recorded as gap.

## FIBONACCI RESULTS
- EXP-01: D1 fib 79.8% (4394) vs rand 81.1% (879); H1 fib 82.8% (6912) vs rand 83.9% (1363). High absolute rates = loose reversal definition, not edge.
- EXP-02: 61.8 D1 79.9% vs others 79.8%; H1 82.7% vs 82.8%. Null.
- Verdict H1/H2: NOT SUPPORTED.

## GEOMETRIC RESULTS
- Only retracements tested. Fans/arcs/circles/time-zones: NOT SUITABLE FOR SYSTEMATIC TESTING (no objective causal definition implemented). Extensions/symmetry/measured moves: deferred.

## CYCLE RESULTS
- Not run (Hurst helper exists, no spectral/autocorr OOS). Deferred — limitation.

## CONFLUENCE RESULTS
- Trend filter (fixed lookback-4 bug mid-study; logged): research H1 50% +0.088R CI [-0.00,+0.17] n=812; validation -0.00R CI [-0.19,+0.18]. No gain.
- Vol filter: only high-vol H1 positive on research; low/mid null. D1 vol splits null/negative.

## WALK-FORWARD RESULTS
- D1 (trend 61.8): -0.12/-0.08/-0.13R (0/3 positive). H1: +0.07/+0.03/+0.15R (3/3 nominally positive, all CIs cross 0). No D1 persistence.

## ROBUSTNESS
- Heat H1 high-vol: SL1.5 lvl 0.5/0.55/0.618/0.65 → +0.14/+0.12/+0.11/+0.11R; SL2.0 +0.08–0.11R; SL1.0 ~0. Partial plateau but SL-sensitive. D1 flat ~0–0.06R.
- Ablation: removing vol filter collapses expectancy to ~+0.03–0.04R (CI crosses 0). Structure filter adds nothing on validation.

## TRANSACTION COSTS
- H1 candidate validation: 1× +0.222R, 2× +0.219R, 3× +0.217R (costs small vs 1.5-ATR stops). Passes cost sweep but irrelevant given OOS failure.

## MONTE CARLO
- Research bootstrap P(mean>0): H1 0.9965 CI [0.04,0.24]; D1 0.81 CI [-0.06,0.19]. In-sample only; validation/final override it.

## MULTIPLE TESTING
- ~20+ configs scanned; 1 nominal research hit (H1 high-vol) expected under null. EXP-01 FDR q>0.5. No White/DSR/PBO computed — gap logged; would further discount the single hit.

## FINAL OOS TEST (single run, frozen FIB-H1-05-HIVOL-001: fade 50%, high-vol, SL1.5, TP2R)
- H1 final 2026-06→09 (n=104): **-0.169R CI [-0.374,+0.051], PF 0.71, win 33.7%**. FAIL.
- D1 final cross-timeframe (n=55): +0.177R CI [-0.16,+0.52], PF 1.37 — wide CI, wrong timeframe, n small. INSUFFICIENT EVIDENCE.
- Strategy not modified after test. Plots: `reports/equity_*`, `mfe_mae_*`.

## FAILURES
- EXP-01/02 null; D1 all variants negative on validation; trend filter null; walk-forward D1 0/3; final OOS negative on native timeframe; structure bug found+fixed mid-study (lookback 3→4, logged).

## LIMITATIONS
- Futures proxy, short H1 window, no spread/volume realism, loose reaction definition inflates absolute rates, no session/HTF/macro confluence, no cycles/geometry beyond retracements, no DSR/WRC/PBO, single swing family in final candidate.

## CONCLUSION
- H1 NOT SUPPORTED. H2 NOT SUPPORTED. H3 PARTIALLY SUPPORTED on research only → NOT SUPPORTED after blind test. H4 INSUFFICIENT EVIDENCE → NOT SUPPORTED. H5/H6/H7/H8/H9/H10 NOT SUPPORTED.
- Overall: **no statistically defensible, reproducible, economically meaningful edge found. A failed hypothesis is a successful research outcome.**
- Next (only with new data/preregistration): Dukascopy/MT5-export tick data, tighter reaction definitions, preregistered single candidate, full DSR/PBO, session-aware tests. No live trading.

## ADDENDUM — Phase 2 (preregistered exploratory, no change to frozen verdict)
- Silver transfer (identical rule): EXP-01 D1 p=0.72, H1 p=0.64 (null). Candidate XAGUSD research D1 -0.50R [-0.59,-0.41] n=447, H1 -0.60R [-0.67,-0.52] n=609; validation H1 -0.16R [-0.37,+0.08]. H8 NOT SUPPORTED — edge does not transfer, contradicts regime-independent geometry.
- Baselines (XAUUSD H1 validation): SMA20/50 +0.016R [-0.05,+0.08]; ATR-20 breakout +0.138R [-0.00,+0.28] n=359 vs fib candidate +0.22R [-0.05,+0.47]. Complex fib does not meaningfully beat simple breakout (overlapping CIs; final OOS fib negative). Per section 18: REJECT.
- Cycles: max|ACF 1–20| D1 0.042, H1 0.048; Hurst ≈0. No persistence. REJECTED.
- Extensions (descriptive only, no control): 1.272 hit 59%, 1.618 hit 42% (n=1704). No edge claim.
- Sessions (post-hoc, multiple-testing warning): asian +0.15, london +0.24, NY -0.03 — all CIs cross 0. Exploratory noise only.
- Overall Phase 2 verdict: strengthens NOT SUPPORTED. No ML launched (unjustified after null simple results). No XAUUSD final re-run.

## ADDENDUM 2 — Close-out
- Causality tests: 3 passed (`tests/test_causality.py`): confirm-lag exact, pairs known at confirm, ATR-NaN warmup skipped.
- Pt/Pd transfer (D1 research, same EXP-01): XPTUSD fib 78.7% vs rand 78.4% p=0.87; XPDUSD 77.6% vs 76.1% p=0.35. Both REJECTED. Full precious sweep (Au/Ag/Pt/Pd) null.
- Visual proof: `reports/fib_examples_random.png` — 4 randomly sampled retracements (rng 42), wins and losses unfiltered. Illustrative only.
- Reproducibility: see REPRODUCIBILITY.md. Final XAUUSD test never re-run.
- Terminal verdict unchanged: NOT SUPPORTED. No trading. No further dredging without preregistration.

## ADDENDUM 3 — Elliott E1 (23.34 steps 1–6; research → validation, final untouched)
- Frequency: D1 61 impulses / 793 ABC / 6 contracting triangles; H1 66 / 986 / 3. Truncation 0; overlap 32/61, 44/66 (majority diagonal-like under strict rules). Barrier/expanding/running triangles, double/triple, W-X-Y-X-Z, leading-vs-ending: NOT RELIABLY DETECTABLE (stubbed, no claim).
- Continuation (research, SL1.5/TP2R/20 bars): D1 +0.21R [-0.16,+0.56] n=61; H1 +0.30R [-0.02,+0.62] n=66. CIs cross 0.
- Falsification (23.31): 8–11x more impulses in real vs shuffled swings — detector responds to real autocorrelation, NOT evidence of predictiveness (forward-R null).
- ABC completion: D1 +0.05R [-0.04,+0.15]; H1 +0.04R [-0.04,+0.12]. Null.
- Fib-wave (23.15): W2 near-grid ≈ chance (29.5–30.3% vs 30%); W4 39–44% vs 30% (n≈60, no FDR control — exploratory only). Extension hits 9–11%. Alternation corr -0.14–-0.19, perm p=0.14–0.25. INSUFFICIENT EVIDENCE.
- Classifier (23.21/23.32): motive-vs-corrective AUC 0.549 in-sample → 0.549 validation. No incremental info over simpler structure; complexity penalty applies — REJECT Elliott features as unnecessary.
- Validation (impulse continuation): D1 n=4 -0.40R; H1 n=13 -0.12R. Costs stable (irrelevant). Criterion 23.35(4) fails.
- Verdict E1: NOT SUPPORTED. No freeze, no final Elliott test (correctly withheld). Steps 7+ (diagonals/complex/degree/nested/partial/probabilistic) not launched — unjustified.
