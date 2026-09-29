# POST-ROUND-5 RESEARCH GAP ANALYSIS (no experiments run)

## 0. History verdicts (frozen, not reopened)
- Fibonacci (E1): retracement reaction vs random null (p 0.33–0.39); 61.8 special null (p≈0.9);
  frozen candidate final OOS −0.17R. NOT SUPPORTED.
- Elliott (E1+E2): impulse/ABC continuation null; classifier AUC 0.55→0.55; diagonals null;
  triangles descriptive-only (no null control); extensions below chance; N-gain flat (0.506–0.516).
  NOT SUPPORTED.
- H1 price action (R3, spot): all 7 events null/negative; breakout_up sign-flipped in validation
  (+0.035 → −0.184R); year-unstable. NOT SUPPORTED.
- Macro daily (R4, repaired stats): 12 interactions null (min q 0.89); +macro AUC 0.520 < 0.526.
  NOT SUPPORTED.
- M1 microstructure (R5): directional path/order claims FAILED validation; reversal-rate
  (F5 ±2pp) + vol-magnitude (F4/F6) replicate but are ~70× smaller than spread; F8 ΔAUC +0.010;
  R-race = chance. Predictive info YES (tiny); edge NO. STOP accepted.

## 1. Genuinely rejected (adequate power, validated null)
Fib reaction/61.8; Elliott continuation/classifier/invalidation/extensions/symmetry; H1 sweeps,
breakouts, failed breakouts, displacement; daily-macro conditioning; M1 path direction, H/L order
direction, efficiency direction; Elliott-specific invalidation (= generic failure).

## 2. Weakly tested (verdict: INSUFFICIENT DATA, not rejection)
- Triangle breakout accuracy (barrier 73–74% — no randomized-triangle control, n≤52, no validation).
- Alternation→W5 AUC 0.64 (n=66, no validation).
- Breakout_up year-heterogeneity (2020 +0.25R vs 2021–23 negative) — regime mechanism uncharacterized.
- Intraday cross-market lead/lag at matched timestamps (only daily macro ever tested; hourly macro
  files exist for 2024+ but were never used in a hypothesis).
- Futures-vs-spot information (never compared).
- Scheduled-event windows (no timestamp feed, never tested).
- Silver/platinum/palladium beyond D1 EXP-01 (transfer question open at M1, low priority).

## 3. Untestable with bid-only OHLC (structural blind spots)
Bid-only M1/H1 cannot observe: true spread and its intraday dynamics (we assumed 0.35+0.15 —
the ENTIRE economic conclusion rests on an assumed number); slippage distribution; quote-vs-trade
deviation; bid-ask bounce decomposition (bid quotes have no transaction bounce, so measured
"reversal" may be quote-smoothing artifact or, conversely, true micro noise may be understated);
trade aggressor side; depth/liquidity; latency/fill probability; weekend-quote vs tradable distinction.

## 4. Candidate families (all NEW info, not indicator recombinations)

### FAM-1. True bid/ask tick + spread dynamics
A. New info: realized spread distribution by session/vol regime; effective vs quoted spread;
   spread-adjusted (net) conditional returns; quote revision intensity.
B. Why unavailable: bid-only OHLC has no ask leg; spread was an assumed constant.
C. Dataset: tick bid+ask prices (+ volumes if available), millisecond timestamps, 2–3y XAUUSD.
D. Source: **Dukascopy tick feed (free**, same venue as current data; serves bid/ask + volumes).
E. Minimum: 2y tick (≈150–250M ticks; process in month chunks) for session×vol cells with ≥10k events.
F. Falsifiable H: "F5 reversal survives spread-adjusted accounting" / "spread predicts subsequent
   |return| beyond vol state."
G. Success: preregistered net-edge CI excludes 0 on validation + replicates across years.
H. Failure: net edge ≤ 0 everywhere (strengthens STOP) or spread explains the reversal (artifact verdict).
I. Risks: tick timestamp vs bar timestamp conventions; feed-specific quotes ≠ retail fills;
   survivorship none (single symbol); volume definition changes.
J. Edge realism: HIGHEST — this is the only family that can convert the 70× spread gap from an
   assumption into a measurement. Either direction (real micro-edge or artifact proof) is decisive.

### FAM-2. Order-flow / aggressor-side proxies
A. New info: signed trade imbalance (tick rule on tick data), quote-rule classification accuracy,
   imbalance→return response curve, toxicity proxies (VPIN-style, volume-clock).
B. Why unavailable: bid OHLC aggregates away who initiated movement; no volume side exists.
C. Dataset: tick price + tick volume (bid/ask volumes separately ideal), 2y.
D. Source: Dukascopy tick volumes (free, proxy-grade); CME GC tick+volume (paid — see FAM-3).
E. Minimum: 2y (VPIN-style buckets need ~50k buckets for stable estimates).
F. H: "signed 50-tick imbalance predicts next-5-min return beyond F5 state (ΔAUC>0.02 validated)."
G/H. Success: validated increment with net accounting; failure: AUC increment ≈0 (flow adds nothing).
I. Risks: tick-rule misclassification (no true aggressor flag on spot FX/CFD); bucket-size mining
   (preregister ONE bucket scheme); volume definition (quote ticks vs traded lots).
J. Edge realism: MEDIUM — needs spread data from FAM-1 anyway; alone it cannot clear costs.

### FAM-3. Futures GC microstructure as incremental info for spot
A. New info: COMEX session volume/imbalance, futures-spot basis dynamics, volume-clock bars,
   futures-led price discovery share (Hasbrouck/Gonzalo-Granger IS).
B. Why unavailable: current data is spot-CFD only; futures bring centralized volume + session structure.
C. Dataset: GC tick or 1-min trades+volume+bid/ask, 2–3y, with session flags.
D. Source: no reliable free full-history source (CME licensed; Databento/Polygon paid tiers;
   Yahoo GC=F intraday capped at ~2y/1h, no aggressor). Honest cost: $$$ — verify before committing.
E. Minimum: 2y covering ≥2 roll cycles + varied vol regimes.
F. H: "GC imbalance/IS-lead improves spot next-M5 prediction beyond F8-C (validated ΔAUC>0.02)."
G/H. Success/failure per preregistered ΔAUC + net accounting with futures commissions.
I. Risks: roll stitching artifacts; session-boundary jumps; spot-vs-futures timestamp sync;
   data-vendor survivorship/selection;Timezone/session definitions.
J. Edge realism: MEDIUM-LOW — highest cost, and spot tradability of a futures signal adds slippage legs.

### FAM-4. Scheduled macro-event behavior (CPI/NFP/FOMC/PCE)
A. New info: pre/post-release drift, volatility cone, reversal-vs-continuation conditional on surprise
   sign (needs vintage, not revised, values).
B. Why unavailable: no timestamp feed existed (R4.5 DATA NOT AVAILABLE verdict).
C. Dataset: release timestamps (minute precision) + vintage actuals + consensus, 2020→present.
D. Source: FMP economic-calendar API (free tier) or FRED release dates (free key) + concurrent
   consensus archive (hardest part — verify coverage before approval).
E. Minimum: ≥30 events per release type (≈2.5y for monthly CPI/NFP).
F. H: "post-CPI 1h |return| exceeds matched no-event windows (permutation p, FDR) AND surprise-signed
   drift replicates on validation half."
G/H. Success: validated, surprise-signed, net of widened event spreads; failure: vol spike with no
   signed edge (the usual outcome — still publishable as a rejection).
I. Risks: timestamp errors (fatal — verify against 3 known 2024 events first); revised vs vintage mix-up;
   consensus-source selection; event-overlap (FOMC minutes vs CPI same week); spread widening unobserved
   without FAM-1 (combine: event study NEEDS spread data).
J. Edge realism: LOW-MEDIUM — classic crowded trade; value is mostly falsification + risk control.

### FAM-5. Cross-market intraday lead/lag at matched timestamps
A. New info: minute-aligned DXY/yields/VIX/SPX/oil states as conditioning variables for XAUUSD M1
   (R4 used daily bars only — this is intraday, causal, matched-clock).
B. Why unavailable: hourly macro was downloaded (2024+) but never tested; 2020–22 intraday macro is a gap.
C. Dataset: DXY/SPX/VIX/oil hourly (already saved, 2024+) + Dukascopy EURUSD tick as USD proxy at M1
   (free, same venue/clock as XAUUSD); yields stay daily (exchange-hours only).
D. Source: existing files + Dukascopy EURUSD M1 (free).
E. Minimum: 2024–26 overlap is enough for discovery+validation ONLY if validated effect is large;
   otherwise extend via Dukascopy majors history (free, same clock).
F. H: "XAUUSD reversal (F5) conditioned on aligned DXY-move sign beats unconditional F5 (validated
   ΔP_up, permutation p, FDR)"; lead-lag cross-correlation profile vs block-permuted null.
G/H. Success: validated increment + year-split stability; failure: flat CC-profile (extends R4 null
   to intraday — a real result).
I. Risks: clock misalignment across venues (verify tick timestamps to the minute first); non-overlapping
   sessions (yields); look-ahead via daily bars (keep prev-day rule); FX-quote vs index staleness.
J. Edge realism: LOW — R4-daily was decisively null; prior for intraday increment is weak. Cheap to test.

## 5. Research-gap matrix
| gap | blocks which verdict | needs new data? | cost | priority driver |
| true spread/net accounting | R5 economic conclusion (assumed 0.35!) | YES tick b/a | free (Duka) | decides artifact-vs-edge |
| aggressor/flow | F5 mechanism | YES tick vol | free proxy | mechanism, not P&L alone |
| futures info share | spot-only ceiling | YES GC tick | $$$ verify | centralized volume |
| event windows | R4-event gap | YES timestamps+vintage | free-ish verify | falsification value |
| intraday cross-market | R4-daily null extension | PARTLY (have 2024+ h1) | free | cheap, weak prior |
| triangle controls | weak-test cleanup | NO (have data) | compute | small-n, low value |
| M1 silver transfer | generality | YES Ag M1 | free (Duka) | low priority |

## 6. Three most justified directions
1. **Tick bid/ask + spread accounting** (FAM-1): free, same venue, attacks the single load-bearing
   assumption of the STOP conclusion; decisive either way.
2. **Intraday cross-market lead/lag** (FAM-5): nearly free (files exist + EURUSD M1), closes the R4
   extension honestly, weak prior acknowledged.
3. **Event-study infrastructure** (FAM-4): high falsification value + risk-control output; gated on
   verifying timestamp+consensus coverage first (no download commitment).

## 7. ONE recommended experiment (approval requested, NOT Round 6)
**TICK-SPREAD VERIFICATION (FAM-1a):** download Dukascopy XAUUSD tick (bid+ask, 2023 validation year
first — cheapest decisive slice), measure realized spread distribution by session×volatility cell,
recompute F5 reversal cells NET of measured spread with the repaired permutation/FDR stack, and
decompose the reversal into spread-crossing vs mid-price continuation. Preregistered decision rule:
net CI>0 on 2023 AND same sign on a 2024 H1 holdout → candidate; else the STOP stands with measured
(rather than assumed) costs, and the F5 regularity is classified as quote artifact or sub-spread noise.
No thresholds optimized, no strategy built, final OOS untouched.
