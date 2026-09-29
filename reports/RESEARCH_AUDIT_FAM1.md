# RESEARCH AUDIT — FAM-1 (Tick-Spread Verification)

Auditor: RESEARCH-AUDITOR (independent, adversarial). Mode: read-only; no code modified, no strategy work, no 2024–2026 price/tick data opened.
Scope: FAM-1 preregistration `reports/PREREG_TICK_SPREAD.md` vs implementation `research/run_tickspread.py`, plus data-flow, firewall, stats, and test coverage.
Severity scale per finding: **PASS / BUG / METHODOLOGICAL RISK / UNTESTED / NOT APPLICABLE**.

---

## A. Executive summary

- **Firewall: PASS.** `research/run_tickspread.py:80,90` hardcodes research `[2020,2021,2022]` and validation `[2023]`; grep over `research/run_tickspread.py` finds no `2024/2025/2026/final_test_data` read path (only the comment at `:2` and the D2 string at `:154` mention `2024+` as a prohibition). `data/dl_tick.py:18` asserts `e <= datetime(2024,1,1)`. Registry contains zero tick entries (`grep -c "tick" research/experiments/registry.jsonl` → 0) and `reports/` contains no `tickspread.json`: the validation calculation has not been run. Prereg cleanliness holds.
- **Net-trade accounting (the decision-driving estimator): PASS on sign/cost conventions.** `research/run_tickspread.py:132-138` fade directions, cost `(se+sx)/2`, `net_usd = direction*(cx-ce)-cost`, normalization by contemporary entry-bar mid-ATR — all match `reports/PREREG_TICK_SPREAD.md:27-30`. Indexing uses `mk[:-1]` (state at bar *t*, move *t→t+1*): genuinely next-bar, no look-ahead.
- **Gross / mid / artifact estimators: FAIL (3 load-bearing bugs).** B1 (contemporaneous instead of next-bar alignment, `:119-120`), B2 (unpaired truncation instead of timestamp-paired difference, `:123`), B3+B4 (wrong return scaling missing `×close`, `:115,117-118`, plus bid-ATR proxy `:101` that is not R5 ATR14). These corrupt the gross sign reference and the artifact decomposition. They do not touch the net estimator's indexing, but B5 means the net decision rule itself is also non-compliant.
- **Decision logic D1/D2: FAIL vs prereg.** Code `:150-154` requires CI strictly *positive* + `q<0.10`; prereg (`reports/PREREG_TICK_SPREAD.md:35-36`) requires CI *excluding 0 (either side)* + `q<0.10` + *same sign as research gross*. Research gross is never computed (`:79-87` spread descriptives only), so the third condition is unenforceable. A significantly negative net would be misclassified as D1 noise.
- **FDR family: DEVIATION.** Code family = 6 (`DIR6`, `:14`); prereg binds 7 (`reports/PREREG_TICK_SPREAD.md:6-7,11`). Code docstring (`:3`) justifies dropping NEU, but the prereg is frozen and was not followed.
- **Test coverage for FAM-1: UNTESTED.** Zero tests touch `run_tickspread.py` helpers (verified by grep over `tests/`).
- **Auditor verdict: NOT CLEARED FOR VALIDATION.** Required fixes B1–B5 (+B6 disposition, B7, B8) must be applied and re-audited before `run_tickspread.py` is executed. Firewall and stats primitives are sound; the FAM-1 estimators and decision gate are not.

---

## B. Repository/data-flow audit

Data flow relevant to FAM-1 (all file:line verified by read):

1. **Acquisition.** `data/dl_tick.py:1-48` — monthly tick fetch → `_tickcache/tick_YYYYMM.pkl` → per-minute aggregates `_tickagg/min_YYYYMM.csv` with columns `timestamp,mid_close,spread_mean,spread_max,n_ticks` (header verified on `min_202001.csv`; 2024+ files never opened or listed beyond a 5-row year-filtered `ls` head showing 2020 names). Firewall assert `:18` blocks `>=2024-01-01`. PASS.
2. **Adjacent acquisition (flagged, not FAM-1 path).** `data/download_duk.py:12` loops `range(2020,2027)` (H1 bid through 2026) and `data/download_m1m5.py:45` spans `2020-01-01→2026-09-29` (found by code grep, not by opening data). These scripts *can* fetch locked years, but `run_tickspread.py` does not import or invoke them. See R5.
3. **Minute loading.** `research/run_tickspread.py:16-27` `load_minutes(years)` reads only requested years from `data/raw/_tickagg`, concats, sorts, `drop_duplicates("timestamp")` (`:24`), coerces UTC (`:25`), keeps `weekday<5` (`:27`, R5-SESSION-001). PASS. Raises `FileNotFoundError` (`:22`) on missing months — fail-loud, acceptable.
4. **M5 construction.** `to_m5` (`:29-46`): resamples `mid_close` → OHLC, `spread_mean` → mean, `n_ticks` → sum (`:31-34`), `dropna` (`:35`), sessions via `MS.add_sessions` (`:36` → `features/microstructure.py:12-17`, bins `0–7 asian / 7–12 london / 12–17 ny / other`), true-range ATR14 (`:37-39`, same formula as `features/microstructure.py:25-27`), `ret = pct_change` (`:40`), vol-state `ret.rolling(240).std().rolling(2000).rank(pct=True)` + `cut [0,.33,.66,1.0]` (`:41-42`, identical to `features/microstructure.py:30-32`). PASS on parity with R5 definitions.
5. **F5 states.** `:43-44` `ret/atr14*close > 0.02 → UP` etc. Dimensional check: `ret≈dC/C`, so `ret×close/atr = dC/ATR` — move in ATR units, threshold 0.02 ATR. Matches prereg deadband intent (`reports/PREREG_TICK_SPREAD.md:6,17`) and R5 construction (`research/run_round5.py:85`, `research/run_round5_val.py:28-29`). NaN warmup rows fall through both comparisons to NEU — conservative, acceptable. PASS.
6. **Bid leg (validation only).** `:93-101`: 2023 bid M1 from `validation_data/XAUUSD_M1_duk.csv` (verified 2023-only: `2023-01-02→2023-12-29, 352949 rows` via header/range check — validation data, firewall-permitted), `MS.session_filter` (`features/microstructure.py:7-10`), resample `close.last` → M5, inner merge with mid M5 (`:99`). Header confirms bid file **has** `high/low` columns, making the `:101` proxy a choice, not a necessity — see B4.
7. **Estimators.** `:110-144` per `DIR6` cell: gross bid, mid genuine, artifact, net fade. Net (`:132-138`) verified correct (Section E). Gross/artifact fail (B1–B4).
8. **Inference.** `bootstrap_mean_ci` (`statsx/permutation.py:20-26`, percentile, B=2000, seed 0) and local `signflip_p` (`:69-74`, two-sided sign-flip, `(c+1)/(B+1)`) match prereg B=2000/seed 0 (`reports/PREREG_TICK_SPREAD.md:10-11,30`). `bh_fdr_real` (`statsx/permutation.py:28-34`) step-up verified algebraically correct (rank-1 → `pmax`, rank-n → `pmin×n`). Imported-but-unused `permutation_diff_p` in `run_tickspread.py:10` — see B6. PASS on primitives, FAIL on wiring.
9. **Decision + logging.** `:146-158`: BH over net p's, D1/D2 strings, `log_experiment(..., status="REJECTED")` hardcoded, `reports/tickspread.json` write. See B5, B6, B7, B8.
10. **Non-FAM-1 context reviewed (no findings imported):** `research/run_phase1.py`, `run_phase2.py`, `run_round3.py`, `run_round4.py`, `run_round5.py`, `run_round5_val.py`, `run_validation.py`, `backtesting/engine.py`, `features/swings.py`, `features/fibonacci.py`, `features/volatility.py`, `features/structure.py`, `validation/splits.py`, `data/adapter.py`, `data/quality.py`, `data/download.py`, registry tail (EXP-000086→EXP-000105, all REJECTED; R5 qmin ≈0.001). R5's documented catches (F2 ATR leak, tz-strip join, R-loop stale entry per `reports/ROUND5_REPORT.md:13-16,48`) show healthy disclosure culture but do not cover FAM-1 code.

---

## C. Firewall audit

| Check | Result | Evidence |
|---|---|---|
| Research years hardcoded | PASS | `research/run_tickspread.py:80` `load_minutes([2020,2021,2022])` |
| Validation year hardcoded | PASS | `research/run_tickspread.py:90` `load_minutes([2023])` |
| No 2024+ reference in FAM-1 code | PASS | grep `2024\|2025\|2026\|final_test_data` over `research/run_tickspread.py` → only prohibitive comment `:2` and D2 string `:154` |
| Bid leg 2023-only | PASS | `:93` reads `validation_data/XAUUSD_M1_duk.csv`; range verified `2023-01-02→2023-12-29` (validation slice, permitted) |
| Tick-fetch firewall | PASS | `data/dl_tick.py:18` `assert e <= datetime(2024,1,1)`; docstring `:2` bans 2024+ |
| Validation calc not yet run | PASS | registry `grep -c tick` → 0; no `reports/tickspread.json` in `reports/` listing |
| `final_test/final_evaluator.py` isolation | PASS with caveat | `:11-13` takes `freeze_path/final_csv` as argv — isolation by invocation, no hardcoded year gate; firewall-by-convention. Not run by auditor. File is strategy-freeze machinery, outside FAM-1 decision path |
| 2024+ data never opened | PASS | No read/stat/row-count of any `*2024*`/`*2025*`/`*2026*` tick, tickagg, dukcache, or `final_test_data/` object. Directory listing restricted to year-filtered head (2020 names only) |
| Adjacent risk (not a breach) | METHODOLOGICAL RISK (R5) | `data/download_duk.py:12`, `data/download_m1m5.py:45` can acquire 2024+ H1; unused by FAM-1 |

One inadvertent-avoidance note: a broad code-grep over `data/` surfaced timestamp *lines* inside `MACRO_DXY_D1.csv` (daily FX macro, not XAUUSD price/tick). No XAUUSD 2024+ price/tick content was inspected; macro files are outside the stated firewall (`tick_*/min_*/_dukcache/final_test_data/validation-of-final-years`).

---

## D. Statistical audit

| Component | Verdict | Detail |
|---|---|---|
| `bootstrap_mean_ci` (`statsx/permutation.py:20-26`) | PASS | Percentile CI, B=2000 default, seed 0, NaN-filtered, `(mean, lo, hi)` return order matches call sites `:122` |
| `signflip_p` (`research/run_tickspread.py:69-74`) | PASS (as a null) | Two-sided sign-flip vs zero-edge null is the correct null for mean net trade return; `(c+1)/(B+1)` smoothing; `B=2000, seed=0` per prereg; `n<30 → p=1.0` guard reasonable |
| `bh_fdr_real` (`statsx/permutation.py:28-34`, duplicate in `statsx/tests.py:27-37`) | PASS (implementation) | Step-up arithmetic verified; monotone; bounded ≤1 |
| BH family actually used | BUG (B6) | 6 net p's; prereg binds 7; gross/mid/artifact have no p despite prereg `permutation_diff_p` language |
| `permutation_diff_p` imported at `:10` but never called | BUG (B6) | Dead import evidences prereg-intended gross/return permutation tests were dropped |
| Paired artifact bootstrap | BUG (B2) | `:123` truncates independently-filtered vectors; prereg `:25-26` demands timestamp-paired `d_i` |
| Shared-seed bootstraps | METHODOLOGICAL RISK (R3) | Fresh `default_rng(0)` per call → identical index streams across cells; per-cell CIs valid, cross-cell contrasts correlated. Negligible impact on D1/D2 |
| Empty-cell NaN → JSON | BUG (B8) | `bootstrap_mean_ci([])` → `(nan,nan,nan)` (`statsx/permutation.py:23-24`); `json.dump` at `:157` would emit invalid `NaN` literals |
| D1/D2 gate | BUG (B5) | Sign condition dropped, research-gross reference absent, one-sided-positive-only gate |
| Multiple-testing leakage (research→validation) | PASS | Research side (`:79-87`) purely descriptive (no p-values); validation FDR computed fresh. No selection on validation |
| Hidden optimization | PASS | No sweeps over thresholds/holdings/sessions/vol-bins in `run_tickspread.py`; `DIR6`, deadband, costs, seeds all literal |
| Registry semantics | BUG (B7) | `:156` logs `status="REJECTED"` unconditionally |

---

## E. FAM-1 formula audit

Prereg spec (`reports/PREREG_TICK_SPREAD.md:13-31`) vs code, line by line:

- **Quoted spread / mid (`s=ask−bid`, `m=(ask+bid)/2`):** PASS. Tick aggregation in `data/dl_tick.py:38-39` computes `mid=(bid+ask)/2`, `spread=ask−bid`; minute bars `mid_close=last`, `spread_mean=mean`, `n_ticks=count` (`:41-46`) match prereg `:15`.
- **Mid-M5 OHLC + mid_ATR14:** PASS. `:31-39` builds OHLC from mid-minute closes with R5-identical true-range ATR14.
- **Session/vol/F5 on MID-M5:** PASS on construction (`:36,41-45`); RISK on use (R2 — mid states condition bid returns; acceptable for pairing, mislabeled "R5 replication").
- **F5 deadband `0.02×ATR`:** PASS (`:43-44`, dimensionally `dC/ATR`; matches R5 `run_round5.py:85`).
- **Gross bid in bid-ATR units:** BUG (B1+B3+B4). `:115` `br = bid_ret/ba` with pct numerator (should be price-diff per R5 `run_round5.py:19-20` / `run_round5_val.py:19-20`) and `:101` `bid_atr = diff.abs.rolling(14).mean()` (should be true-range ATR14; bid `high/low` exist). Scale off by ~`1/close` (≈1/1900 at XAUUSD prices) *and* denominator-concept mismatch vs mid leg.
- **Mid genuine in mid-ATR units:** BUG (B1+B3). `:117-118` same pct-without-`×close` error (mid ATR itself is correct true-range).
- **Artifact `d_i = bid_ret_i − mid_ret_i`, bootstrap of difference:** BUG (B1+B2+B3+B4). Misaligned (B1), unpaired (B2), mixed units (B3+B4).
- **Net fade signs:** PASS. `:132` `direction=-1` for `UP/UPUP/DNUP` (fade UP→short), `+1` otherwise (fade DN→long) matches prereg `:27-28`.
- **Cost `(spread_entry+spread_exit)/2`:** PASS. `:134,137` use M5 `spread` (mean-of-minute-means) for entry/exit bars; algebra `direction*(cx-ce)−cost` verified correct for both long (buy ask/sell bid) and short (sell bid/buy ask).
- **Horizon next-M5 close-to-close on mid:** PASS on indexing (`:133-134` `mk[:-1]`); RISK on gaps (R1 — inner-merge row adjacency may exceed 5 min over missing bars).
- **Net units of contemporary mid-ATR:** PASS. `:135-138` normalize by entry-bar `ma` with `ae>0` + finite guard (`:136`).
- **Research gross sign reference:** UNTESTED / missing (B5). Research block (`:79-87`) emits spread descriptives + `__overall__` only.
- **Effective vs quoted spread:** NOT APPLICABLE to prereg metrics (quoted only, `:28`); the GAP-analysis effective-spread question (`reports/GAP_ANALYSIS.md:42,55`) remains UNTESTED by design.
- **C residual:** NOT APPLICABLE per prereg (`:31` — no separate quantity; CI width only). Code consistent (no C quantity).

---

## F. Test coverage audit

- `tests/test_causality.py:1-31` — fractal confirm lag, pairs-known-at-confirm, ATR warmup. PASS for Phase-1 features; does not touch FAM-1. Coverage of `run_tickspread.py`: none.
- `tests/test_leakage.py:1-54` — `m5_frame`/`f3_order`/`efficiency`/`f2_formation` recomputation identity + session-rule doc check. PASS for R5 microstructure; `to_m5`/`load_minutes`/`masks`/`spread_cells`/`signflip_p`/net accounting untested. Note `to_m5` duplicates `MS.m5_frame` logic rather than reusing it — drift risk between the two copies (currently in sync on ATR/vol/rank/session per B-audit items 4–5, but no test pins this).
- `tests/test_stats.py:1-23` — permutation sensitivity + FDR monotonicity on synthetic data. PASS for primitives; `signflip_p` and the D1/D2 gate have no tests.
- FAM-1–specific coverage: **UNTESTED** — no test for minute→M5 timestamp alignment, bid/mid merge alignment, gross-vs-net indexing consistency, paired artifact construction, cost/sign algebra, ATR parity, NaN guards, or D-logic truth table.
- Verification discipline: grep confirms no test file references `tickspread|signflip|load_minutes|spread_cells` (only `run_tickspread.py` itself defines them).

---

## G. Bugs found

**B1 — Gross/mid/artifact are contemporaneous, not next-bar (look-ahead). SEVERITY: high.**
File `research/run_tickspread.py:119-120`:
```python
g = br[1:][mk[1:]] ... ; m_ = mr[1:][mk[1:]] ...
```
`br[1:][k]` is the move `close[k]→close[k+1]` while `mk[1:][k]` is the F5 state *at* `k+1`, which is itself constructed from that same move (`:43-44`). The prereg metric is "mean **next**-M5" (`reports/PREREG_TICK_SPREAD.md:23`). The net estimator in the same loop correctly uses `mk[:-1]` (`:133-135`). So gross pairs each return with its own sign — UP cells mechanically positive, DN mechanically negative — and the artifact is built on the same misalignment. *Why wrong:* state at `t` must condition the move `t→t+1`, i.e. `br[1:][mk[:-1]]`. *Impact:* gross sign reference invalid; artifact CIs meaningless; D2's (unenforced) sign check would reference a corrupted sign. Net verdict numerically unaffected (separate indexing). *Minimal fix (do not apply):* change `:119-120` masks to `mk[:-1]` for `g`/`m_`, matching `:133-135`.

**B2 — Artifact difference is positionally truncated, not timestamp-paired. SEVERITY: high.**
File `research/run_tickspread.py:122-124`:
```python
g = g[np.isfinite(g)]; m_ = m_[np.isfinite(m_)]
d = g[:len(m_)]-m_[:len(g)] ...
```
Prereg (`reports/PREREG_TICK_SPREAD.md:25-26`) requires paired-by-timestamp `d_i = bid_ret_i − mid_ret_i`. Independent finite-filtering followed by length truncation pairs the *k-th finite* bid return with the *k-th finite* mid return, which are different bars whenever NaN patterns differ (they do: bid warmup `:101` vs mid warmup `:39`, plus merge-gap pct artifacts). *Impact:* artifact mean/CI mixes unpaired observations; direction and width both unreliable. *Minimal fix:* compute a joint finite mask on the aligned frame (`np.isfinite(br)&np.isfinite(mr)&mask`) *before* splitting into `g`/`m_`, then `d = g-m_` elementwise.

**B3 — Returns scaled by pct/ATR-price instead of price-diff/ATR (missing ×close). SEVERITY: high for characterization.**
Files `research/run_tickspread.py:115,117-118`. R5 convention (`research/run_round5.py:19-20`, `research/run_round5_val.py:19-20`) is `(close.shift(−1)−close)/atr14` — dimensionless ATR units. Code uses `pct_change()/atr_price`, i.e. units of inverse-dollars, smaller by ~`1/close` (≈1/1900). The deadband (`:43-44`) correctly includes `×close`, proving the author knew the conversion. *Impact:* gross/mid/artifact means and CIs are mis-scaled ~3 orders of magnitude; any comparison to R5 magnitudes or to net (correct price/price units) is invalid. D1/D2 gate uses net only, so the verdict trigger is numerically unaffected — but the artifact decomposition, the prereg's headline purpose, is. *Minimal fix:* `br = m5.bid_close.diff()/bid_atr_true_range`, `mr = m5.close.diff()/ma` (or equivalently `ret×close/atr`).

**B4 — Bid ATR is a close-diff proxy, not R5 ATR14. SEVERITY: medium (compounds B3).**
File `research/run_tickspread.py:101`: `m5.bid_close.diff().abs().rolling(14).mean()`. R5/mid ATR14 is true-range `max(h−l, |h−c_prev|, |l−c_prev|)` rolling-14 (`:37-39`, `features/microstructure.py:25-27`). The bid M1 source has `high/low` (verified header), so true-range was available. Since `mean|Δclose| ≤ mean(TR)`, the proxy denominator is systematically smaller → `br` systematically inflated relative to `mr`, biasing the artifact positive-or-negative depending on cell. *Impact:* even after fixing B3, mixed ATR concepts across legs invalidate "same units" (`reports/PREREG_TICK_SPREAD.md:25`). *Minimal fix:* build bid M5 OHLC from bid M1 (`MS.m5_frame`-equivalent) and use its true-range `atr14`.

**B5 — D2 sign condition dropped; research gross never computed; D1 misclassifies negative significance. SEVERITY: high (decision logic).**
Files `research/run_tickspread.py:79-87` (research block: spread cells only) and `:150-154`:
```python
ok_cells = [k for k in DIR6 if out["net"][k]["ci95"][0] > 0 and out["net"][k]["q"] < 0.10]
```
Prereg D2 (`reports/PREREG_TICK_SPREAD.md:35-36`): "net CI **excluding 0** AND q<0.10 AND **same sign as research gross**". Three deviations: (i) code demands strictly positive, so a significantly *negative* net (real momentum — still a phenomenon) falls through to D1's "quote artifact or sub-cost noise" text, a misclassification; (ii) the research-gross sign table does not exist anywhere in the script, so the third conjunct cannot be evaluated; (iii) D1's text (`:152`) inherits the distortion. *Impact:* the gate that converts numbers into the FAM-1 verdict does not implement the bound rule. *Minimal fix:* compute research-side (2020–22) gross fade-implied signs per DIR6 cell with the *corrected* next-bar alignment, then `ok_cells = [k for k in DIR6 if (ci excludes 0, either side) and q<0.10 and sign(net[k])==sign(research_gross[k])]`; rewrite D1 text to distinguish "no significance" from "significant but sign-mismatched".

**B6 — FDR family is 6, prereg binds 7; gross/return permutation tests missing. SEVERITY: medium.**
Files `research/run_tickspread.py:14` (`DIR6` — NEU dropped), `:144` (`P` collects net p's only), `:10` (dead `permutation_diff_p` import). Prereg (`reports/PREREG_TICK_SPREAD.md:6-7,11`): "7 tests total … BH-FDR across the 7 F5 cells" with `permutation_diff_p` on trade/return vectors. The module docstring (`:3`) argues NEU has no fade direction — reasonable scientifically, but the prereg is frozen and the deviation is undisclosed in outputs. A 6-family q is anti-conservative relative to the bound 7-family. *Impact:* any D2 `q<0.10` claim would rest on a narrower family than preregistered. *Minimal fix:* report both (6-net q for the tradability gate *and* 7-cell sensitivity including NEU gross/mid permutation p's), flag the deviation explicitly in `tickspread.json` and the registry record; do not silently keep 6.

**B7 — Registry status hardcoded REJECTED. SEVERITY: low.**
File `research/run_tickspread.py:156`: `status: "REJECTED"` regardless of the D1/D2 branch. A D2 candidate outcome would be permanently mislabeled in the append-only log. *Minimal fix:* `status = "PROMISING" if ok_cells else "REJECTED"` (or a dedicated `CANDIDATE` label), consistent with registry conventions elsewhere.

**B8 — NaN CIs produce invalid JSON on empty cells. SEVERITY: low (latent).**
Files `statsx/permutation.py:23-24` + `research/run_tickspread.py:157`. An empty return vector yields `(nan,nan,nan)`; `json.dump` emits `NaN` literals (invalid JSON, downstream-parse hazard). Unlikely with 2023 sample sizes but unguarded. *Minimal fix:* coerce non-finite CI endpoints to `None` before serialization, or skip+flag empty cells.

---

## H. Risks found

**R1 — Inner-merge gap skipping makes "next M5" row-adjacent, not clock-adjacent.** `research/run_tickspread.py:99` inner-joins mid and bid M5; `:133-134` take consecutive *rows*. Over missing-minute stretches (dropped by `:35` `dropna` or absent months), one "next bar" can span >5 min of wall time with a different spread regime. *Verdict impact:* low — tickagg density is high and both legs share the gap, but the holding period is not strictly uniform. Recommend asserting modal 5-min spacing and reporting gap rate.

**R2 — "R5 replication" label overstates a mid-state-conditioned gross.** `:102` conditions bid returns on mid-M5 states (correct for pairing; prereg `:17` mandates mid cells). R5 states were bid-M5 states, so the gross is not a literal replication. *Verdict impact:* none on the net gate, but the sign-reference comparison in D2 mixes state definitions. Disclose in outputs.

**R3 — Shared deterministic bootstrap streams.** Every `bootstrap_mean_ci` call re-seeds `default_rng(0)` (`statsx/permutation.py:21`). Per-cell CIs are valid; cross-cell inference shares randomness. *Verdict impact:* negligible for D1/D2 thresholds.

**R4 — `spread_cells` minute→M5 assignment cost and merge-blindness.** `:55-66` uses `floor("5min").isin(lab)` per cell (108 isin scans) and counts minutes even for M5 bars later dropped by the bid merge. *Verdict impact:* performance only; research/validation spread tables remain descriptive and pre-merge consistent.

**R5 — 2024+ acquisition capability exists outside the FAM-1 path.** `data/download_duk.py:12` (`range(2020,2027)`), `data/download_m1m5.py:45` (through 2026-09-29). Neither is imported by `run_tickspread.py` (verified by read). *Verdict impact:* none provided these scripts are not executed for FAM-1; recommend a repo-level firewall note so a future operator does not refresh raw data into the locked window.

**R6 — Weekend-gap ATR continuity.** Resampling after weekend filtering treats Friday-close→Monday-open as adjacent in ATR/return windows (both legs identically). *Verdict impact:* negligible; symmetric across legs.

**R7 — Net pooled across sessions/vol.** Prereg requires net per F5 cell only; session×vol net splits are absent by design. *Verdict impact:* none — but a pooled null could mask an offsetting session-specific edge; note as a limitation, not a fix (adding splits would breach the no-optimization rule without a prereg amendment).

---

## I. Required fixes before validation

All items refer to `research/run_tickspread.py` unless noted. **Do not run the script until 1–5 are fixed and re-audited.** (Prereg `reports/PREREG_TICK_SPREAD.md` is frozen and must not be edited to match the code — the code must be brought to the prereg.)

1. **Fix next-bar alignment (B1):** `:119-120` → mask `br[1:]`/`mr[1:]` with `mk[:-1]` (state at *t*, move *t→t+1*), identical to the net convention at `:133-135`. Add an assertion that gross and net use the same mask convention.
2. **Fix paired artifact (B2):** build one joint finite mask on the aligned frame before splitting into `g`/`m_`; `d = g − m_` elementwise. Delete the truncation expression at `:123`.
3. **Fix return/ATR units (B3+B4):** replace `:101` with a true-range bid ATR14 built from bid M5 OHLC (reuse the `:37-39` formula or `MS.m5_frame`); replace `:115,117-118` with price-difference returns (`diff/atr`) on both legs so gross/mid/artifact are in ATR units matching R5 and the net estimator.
4. **Implement the bound D2 rule (B5):** compute 2020–22 research gross fade-implied signs per DIR6 cell (corrected alignment); gate D2 on *CI excludes 0 either side* + `q<0.10` + *sign(net)==sign(research gross)*; separate D1 "no significance" text from "significant but sign-mismatched" (the latter must not read as artifact/noise).
5. **Resolve the 6-vs-7 family (B6):** keep the 6-cell net gate only with an explicit deviation record, or preferably report 7-cell sensitivity (NEU gross/mid permutation p's via the imported `permutation_diff_p`) alongside; remove the dead import or use it. Record whichever family the decision used in `tickspread.json`.
6. **Fix registry status + JSON robustness (B7+B8):** branch the logged status on `ok_cells`; coerce non-finite CI endpoints to `None`.
7. **Add FAM-1 tests (currently UNTESTED, §F):** causality/alignment test (gross and net share `mk[:-1]`), timestamp-paired artifact test on synthetic frames with staggered NaNs, cost/sign algebra test (long+short), ATR-parity test (bid ATR equals true-range construction on synthetic OHLC), D-logic truth table (positive/negative/sign-mismatch cases), and a firewall test asserting no `2024+` year literal or `final_test_data` reference in the module.
8. **Re-audit, then run once:** re-run this audit's §§C–E against the patched file; only then execute the research→validation sequence. The registry is still clean (0 tick entries) — keep it that way until clearance.

---

## J. Final auditor verdict

- **Firewall: PASS.** Research/validation separation is correctly hardcoded; the tick-fetch assert holds; no 2024–2026 price/tick data was accessed; the validation run has not occurred.
- **Stats primitives: PASS.** Bootstrap, sign-flip null, and BH step-up implementations are correct and prereg-conformant in parameters.
- **FAM-1 estimators: FAIL.** The decision-driving net-trade estimator is correctly signed, costed, normalized, and indexed — but the gross/mid/artifact estimators carry three compounding bugs (B1 contemporaneous alignment, B2 unpaired differences, B3+B4 unit/denominator errors), the D1/D2 gate does not implement the bound rule (B5), and the FDR family deviates from preregistration (B6), with registry/serialization defects (B7/B8) on top.
- **Test coverage for FAM-1: UNTESTED.**
- **Overall: NOT CLEARED FOR VALIDATION.** The script must not be executed in its current state — running it would spend the one-shot validation on numbers known to be misaligned and mis-scaled, while logging a decision under a non-compliant gate. Implement §I items 1–7, request re-audit, and only then proceed. The STOP conclusion from prior rounds is unaffected by this audit (no new numbers were produced).

---

## K. Re-audit (2026-09-29) — fixes commit 3ac2e6f on top of f9435de

Re-audit scope: `research/run_tickspread.py` (314-line rewrite, `def main()` + `__main__` guard) and new `tests/test_tickspread.py`, checked line-by-line against prereg `reports/PREREG_TICK_SPREAD.md` (frozen) and each §G/§H finding. Read-only; no 2024–2026 price/tick data opened (bid-file checks restricted to header + timestamp min/max of the permitted 2020–22 and 2023 files).

- **Prereg frozen: CONFIRMED.** `git diff f9435de HEAD -- reports/PREREG_TICK_SPREAD.md` is empty. Diff touches only the two intended files.
- **Tests pin the properties: CONFIRMED.** `tests/test_tickspread.py`: 13 passed; full suite 24 passed (`.venv/bin/python -m pytest -q`). Tests use synthetic frames only (no real data reads). Each claimed property has a live assertion (numeric + source-grep); the B3 placeholder expression (`if False else None`, `test_tickspread.py:94-95`) is dead code inside a real magnitude-ratio assertion — cosmetic, not vacuous.
- **Firewall still holds: CONFIRMED.** Loader calls remain `load_minutes([2020, 2021, 2022])` / `load_minutes([2023])`; `2024+` appears only in prohibitive comment/docstring contexts (`run_tickspread.py:2,290`); no `final_test_data` reference; registry `grep -c -i tick` → 0; `reports/tickspread.json` still absent (validation not run). Research bid file verified 2020-01-01→2022-12-30, validation bid file 2023-only (timestamp range checks on permitted years); both headers confirm `high/low` columns exist, so true-range bid ATR was feasible as implemented.

### Finding-by-finding re-classification (with file:line evidence)

| ID | Verdict | Evidence |
|---|---|---|
| B1 (next-bar alignment) | **FIXED** | `run_tickspread.py:89-98` `next_ret_diff` = `(close.shift(-1)-close)/atr`; validation loop `:220-222` (`gb/gm = .values[:-1]`, `k = mk[:-1]`) and research `:152-154` share the identical state-at-*t* convention with length asserts; contemporaneous `mk[1:]` fully gone (grep: no match). Pinned by `test_b1_next_bar_alignment` + `test_b1_gross_net_share_mask_convention`. |
| B2 (paired artifact) | **FIXED** | `:225-227` single joint finite mask, `d = g - m_` elementwise; truncation expression deleted (grep: no match). Pinned by `test_b2_paired_artifact` (staggered-NaN synthetic distinguishes paired vs truncated). |
| B3 (diff/ATR units) | **FIXED** | `next_ret_diff` uses price-diff, no `pct_change` (grep: absent from function body); state deadband `:60-61` retains the correct `ret/atr*close` form. Pinned by `test_b3_diff_over_atr_units` (magnitude-ratio assertion). |
| B4 (true-range bid ATR) | **FIXED** | `build_bid_m5` `:72-86` builds bid M5 OHLC from M1 `high/low` + true-range `max(h-l,\|h-c_prev\|,\|l-c_prev\|)` rolling-14, same formula as mid leg `:54-56`; close-diff proxy gone (grep: no match). Pinned by `test_b4_bid_atr_true_range` (series-equal vs manual true-range) + `test_atr_parity_mid`. |
| B5 (bound D2 rule) | **FIXED** | `research_gross_signs` `:134-159` computes 2020–22 bid-based gross signs per DIR6 with corrected alignment, called at `:195` **before** any validation gating; D2 `:272-280` requires CI-excludes-0-either-side (`_ci_excludes_zero`, `:162-166`) + `q<0.10` + `sign(net)==sign(research gross)`; D1 `:281-287` separates sign-mismatch from no-significance; negative-significant nets enter `ok_cells` with sign (phenomenon, "NOT strategy" — not misclassified as noise, not claimed as positive edge). Pinned by `test_d_logic_truth_table` + `test_cost_sign_algebra`. |
| B6 (7-cell family) | **FIXED** | `FAMILY7` `:19` = UP/DN/NEU/UPUP/DNUP/UPDN/DNDN; NEU enters the same BH family via `permutation_diff_p(x1, x0)` return-vector p `:255-257` (defaults B=2000/seed 0 confirmed in `statsx/permutation.py:5`, NaN-filtering built in); dead import now used; `q` mapped with `zip(FAMILY7, q)` `:264-265` in loop order. Pinned by `test_fdr_exact_7cell_family` + `test_permutation_import_used`. Prereg-reading note: "7 tests total (3+4)" (`PREREG:6-7,11`) supports NEU-inclusive-7; the "NEU excluded" parenthetical refers to R5's research-set convention. |
| B7 (registry status) | **FIXED** | `:291` `status = "PROMISING" if ok_cells else "REJECTED"`; no hardcoded `status": "REJECTED"` remains. Pinned by `test_no_hardcoded_rejected_status`. "PROMISING" is consistent with registry conventions; decision text carries the prereg "candidate" wording. |
| B8 (NaN-safe JSON) | **FIXED** | `_finite_float` `:23-31` coerces non-finite → `None`, applied to every CI/mean output (`:157,230-234,247-248`); `json.dump(..., allow_nan=False)` `:296` fails loud instead of emitting invalid literals. Pinned by `test_json_no_nan`. |
| Import safety (§I.7 prerequisite) | **FIXED** | Module body wrapped in `def main()` `:180`, `if __name__ == "__main__"` guard `:302-303`; tests import the module with zero side effects. |
| R1 (row- vs clock-adjacent "next M5") | **STILL OPEN (residual risk, low)** | Inner-merge + row-adjacency unchanged (`cell_frame` `:128`, net `:239-241`). Impact unchanged: low (shared gaps, dense bars). Non-blocking; recommend a modal-spacing/gap-rate assertion at run time. |
| R2 (mid-state-conditioned gross label) | **ADDRESSED (disclosure)** | `cell_frame` docstring `:122-126` + `research_gross_signs` docstring state mid-states-per-prereg explicitly. Non-blocking. |
| R3 (shared bootstrap seeds) | **STILL OPEN (negligible, by design)** | `bootstrap_mean_ci` unchanged (seed 0 per call). Per-cell CIs valid; accepted as negligible per prior audit. Non-blocking. |
| R4/R5/R6/R7 | **UNCHANGED / NOT APPLICABLE** | Perf-only (R4), outside-path acquisition capability (R5), symmetric weekend adjacency (R6), pooled-net by prereg design (R7). None touch the verdict gate. |

### New observations (notes, NOT blockers)

- **N1 (label imprecision):** `research_gross_signs` docstring says "fade-implied sign" but the stored sign is the raw gross-mean sign (no `FADE_DIR` multiplication, `:157-158`). The D2 comparison implemented is the literal-prereg `sign(net)==sign(research gross)` — compliant; only the docstring adjective is imprecise.
- **N2 (fail-loud, acceptable):** `spread_cells` descriptives use bare `round(float(...))` rather than `_finite_float`; a NaN spread would raise under `allow_nan=False` instead of corrupting output. Fail-loud is the safe direction.
- **N3 (conservative divergence, disclosed):** cells with `n<30` store the raw sign-flip `p` but contribute `1.0` to the BH vector (`:250`). Conservative; visible in code.

### Final re-audit verdict

- **Firewall: PASS.** Separation hardcoded; locked years untouched; validation not yet run (registry clean, no output JSON).
- **FAM-1 estimators: PASS.** Gross/mid/artifact are next-bar-aligned, timestamp-paired, ATR-unit estimators sharing the net convention; prereg-literal D1/D2 gate with the research-gross reference computed pre-gating; exact 7-cell FDR; branched status; NaN-safe serialization.
- **Test coverage for FAM-1: PASS.** 13 targeted regression tests, all green; full suite 24 green.
- **Overall: CLEARED FOR VALIDATION.** `research/run_tickspread.py` may now be executed **once** for the research→validation sequence (expected artifacts: `reports/tickspread.json` + one registry entry). Constraint carries forward: no 2024–2026 reads, no threshold/holding/cell re-tuning on the result — D1/D2 as computed stands. The STOP conclusion from prior rounds remains in force until that single run reports D2.
