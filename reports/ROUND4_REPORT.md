# ROUND4_REPORT.md — XAUUSD Cross-Asset / Macro Conditional Research (prereg R4-001)
E1/E2/E3 closed and untouched. Reused ONLY Round-3 events. Primary spot H1 (research 2020–22, validation 2023, final 2024–26 LOCKED, unrun). Macro = causal prev-day daily features. Gaps: H1 macro 2020–22 DATA GAP; NASDAQ DATA GAP; 2Y = ^IRX proxy; real yield = TIP proxy; CPI/NFP/FOMC DATA GAP (no feed).

## Interactions (12 preregistered, research spot+macro)
- breakout_up × DXY down: -0.020R [-0.13,+0.09], n=526.
- breakout_up × DXY downtrend50: +0.103R [-0.02,+0.23], n=398.
- breakout_up × Y10 down (1d/5d): +0.058R / +0.109R, CIs cross 0.
- sweep_high × DXY up / Y10 up: -0.135 / -0.172R, null.
- breakout_up × SPX up: research not shown above (null); validation -0.251R [-0.42,-0.08].
- breakout_up × TIP up / OIL up: validation -0.281R / -0.228R (CIs negative).
- breakout_up × VIX hi, sweep_high × VIX hi, failed × DXY_any: n=0 — INSUFFICIENT DATA (filter/mapping gap, not evidence).

## Validation (2023)
All 12 null or negative. Best research hints (+0.10R) collapse or sign-flip. NOTHING SURVIVES.

## Information gain (logistic, validation)
- A (XAUUSD-only): AUC 0.5255, Brier 0.2355, logloss 0.6638.
- B (+macro): AUC 0.5199, Brier 0.2359, logloss 0.6647. Macro WORSENS all three. Answer: NO gain.

## Baselines
Macro-conditioned events do not beat XAUUSD-only events (which were already null); XAUUSD-only breakout_up research +0.035R vs macro splits mostly lower.

## Answers
1. DXY adds information? NO.
2. US yields add information? NO.
3. VIX adds information? NO (hi-regime cells empty; elsewhere null).
4. Macro regimes change XAUUSD event distributions? No validated change.
5. Macro beats XAUUSD-only? NO — AUC/Brier/logloss all worse.
6. Anything survives validation? NOTHING.
7. Freeze one strategy? NO. STOP. No final OOS. Do not trade.
