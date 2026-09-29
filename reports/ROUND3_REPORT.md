# ROUND3_REPORT.md — XAUUSD Conditional Market Structure (prereg R3-001)
E1/E2 closed and untouched. Primary: Dukascopy **spot** XAUUSD H1 (39,862 bars 2020–2026; splits 17,749/5,890/16,223). Yahoo GC=F used ONLY as secondary futures proxy, never mixed. Fixed exec SL1.5/TP2R/20. Final OOS NOT run (no validation survivor → STOP per spec).

## Regimes/sessions/events (thresholds pre-defined in research/run_round3.py)
- Regimes: vol low/mid/high (ATR pct), trend_state, efficiency range/trend, ATR expansion/contraction (1.2/0.8), range expansion/compression (1.5/0.7), sessions asian/london/ny (UTC 0-7/7-12/12-17).
- Events (causal, entry next bar): sweep_high/low, breakout_up/down, failed_breakout, displacement, large_range.

## Conditional results — research (primary spot)
- sweep_high: n=634, exp -0.192R [-0.28,-0.10] — NOT SUPPORTED (fading loses).
- sweep_low: -0.017R [-0.13,+0.10] — NOT SUPPORTED.
- breakout_up: +0.035R [-0.04,+0.11], p=0.055 vs random, q=0.57 — NOT SUPPORTED (CI crosses 0, FDR null).
- breakout_down: -0.030R [-0.12,+0.06] — NOT SUPPORTED.
- failed_breakout: -0.105R [-0.18,-0.02] — NOT SUPPORTED.
- displacement: -0.062R [-0.12,-0.01] — NOT SUPPORTED.
- large_range: -0.039R [-0.11,+0.03] — NOT SUPPORTED.
- Baselines: random -0.076R [-0.13,-0.02]; prev-bar -0.027R; trend -0.016R. Nothing beats baselines after FDR (all q=0.57).
- Interactions (preregistered only): all CIs cross 0 or negative (e.g. failed×ny -0.20R [-0.33,-0.08]).

## Validation (primary spot, 2023)
- breakout_up -0.184R [-0.32,-0.05] (SIGN FLIP vs research +0.035). sweep_high -0.108, sweep_low -0.153, failed -0.007, displacement -0.043, large_range -0.006 — all CIs cross 0 or negative. NOTHING VALIDATED.

## Robustness
- Years (breakout_up): 2020 +0.246R [+0.11,+0.39]; 2021 -0.084R; 2022 -0.116R; 2023 (val) -0.184R. Regime-unstable: isolated-year positive ≠ edge.
- Secondary Yahoo GC=F (2024–26): breakout_up +0.188R [+0.09,+0.29] but primary validation negative and years unstable — cross-dataset disagreement CONFIRMS fragility; not used to rescue XAUUSD.
- XAGUSD secondary not run (unjustified after primary null).

## ML
Not launched (no survivors to combine). Correctly withheld.

## Strategy
NONE frozen. Manufacturing one would violate anti-p-hacking rules.

## Terminal answers
1. Conditional predictive structure? NOT SUPPORTED — no event shows a stable, validated distributional edge.
2. Variables surviving validation? NONE.
3. Any event beating baselines? NO (after FDR + validation).
4. Any effect surviving OOS? OOS not run (no qualifier); validation itself failed.
5. Evidence for one frozen strategy? NO. STOP. Do not trade.
