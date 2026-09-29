# PREREGISTRATION — TICK-SPREAD VERIFICATION (no Round number)
Status: PREREGISTERED. No validation calculation has been run. Final OOS 2024–2026 untouched and will not be read.

## Frozen inputs (from R5, unmodified)
- F5 states: M5 grid, bid-close returns, deadband 0.02×ATR (ATR = M5 ATR14), labels UP/DN/NEU;
  2-state sequences UPUP/DNUP/UPDN/DNDN. 7 tests total (3 + 4). NEU excluded (as in R5 research set:
  F5_1 UP/DN/NEU were computed; family = the 7 UP/DN-involving cells).
- Sessions: asian/london/ny/off (UTC 0–7/7–12/12–17/other), Mon–Fri only (R5-SESSION-001).
- Vol states: LOW/NORM/HIGH from 240-bar RV 2000-bar quantile (R5 definition, used only for spread cells).
- Stats: permutation_diff_p (B=2000, seed 0) on trade/return vectors, bootstrap 95% CI (B=2000),
  BH-FDR across the 7 F5 cells. Significance bar: two-sided CI excludes 0 AND q<0.10.

## Tick processing (Dukascopy xau/usd tick: timestamp, bid, ask; volumes kept if present)
- Quoted spread s(t) = ask(t) − bid(t) [USD/oz]. Mid m(t) = (ask+bid)/2.
- Per-minute bars: mid_close = last mid; spread_mean = mean quoted spread; tick_count.
- Mid-M5 bars: open/high/low/close from mid-minute closes; mid_ATR14 (same formula as R5 M5 ATR14).
- Session/vol/F5 cells recomputed on MID-M5 with identical code paths (deadband uses mid_ATR14).

## Cells for spread distribution (research 2020–22 characterization; validation 2023 confirmation)
spread by: session (4) × vol state (3) × F5 1-state (UP/DN/NEU): mean, median, p90, n_ticks.

## Effect metrics (validation 2023; research 2020–22 gross only for sign reference)
1. Gross (bid, R5 replication): P(up next M5 | state), mean next-M5 in bid-ATR units + bootstrap CI.
2. Mid genuine (B): same on mid-M5.
3. Spread artifact (A): A = gross_bid_mean − mid_mean (same units). CI via bootstrap of the difference
   (paired by timestamp: d_i = bid_ret_i − mid_ret_i; bootstrap mean of d).
4. Net fade trade: fade DN→long (buy ask, sell bid), fade UP→short (sell bid, buy ask);
   horizon next M5 bar close-to-close on mid; cost = (spread_entry_bar_mean + spread_exit_bar_mean)/2;
   net_usd = signed_mid_move − cost; also in units of contemporary M5 mid-ATR.
   Report mean net, CI95, permutation p vs zero-edge null (sign-flip permutation), n.
   (C residual = sampling noise around these estimates, quantified by CI width; no separate quantity.)

## Decision rules (bind before calculating)
- D1: If all 7 net CIs include 0 → F5 = quote artifact or sub-cost noise. STOP stands.
- D2: If ≥1 cell has net CI excluding 0 AND q<0.10 AND same sign as research gross → record as
  CANDIDATE MICROSTRUCTURE PHENOMENON (not a strategy). Do not inspect 2024–2026. Stop.
- D3: If tick acquisition for 2020–23 is infeasible → STOP; report that locked OOS prevents completion
  without re-partitioning. No 2024+ access under any circumstance in this experiment.

## Forbidden
Threshold/holding/F5/session/vol-bin/spread-filter/entry-timing optimization; strategy construction;
any read of 2024–2026 data (no file listing content beyond confirming lock integrity by filename only
if needed — preferably not even that).
