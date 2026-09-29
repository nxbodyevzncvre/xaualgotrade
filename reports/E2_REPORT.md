# E2_REPORT.md — Advanced Elliott Structural Research, first batch (A/B/F/G)
Prereg: E2-ABFG-001. Fixed execution SL 1.5 ATR / TP 2R / hold 20. E1 CLOSED and untouched. No final OOS run.

## 1. Structures tested
- A: diagonal-like (overlap + converging trendlines + shrinking ATR width) vs generic converging 6-swing null.
- B: contracting / barrier / expanding / running_suspect triangles, classified strictly before 20-bar outcome window.
- F: partial prefixes 1-2, A-B, 1-2-3start, tri-A-B-C-D (causal; features only to prefix confirm).
- G: W2/W4 invalidation events vs generic swing-failure null; outcome = 0.5-ATR reversal in 5 bars.

## 2. Structures rejected as non-detectable
- Leading vs ending diagonal split: NOT RELIABLY DETECTABLE (position needs subjective larger count) — single diagonal-like class used.
- Double/triple/W-X-Y-X-Z: not implemented this batch (deferred with E2-C); no claim.
- Running triangle: implemented only as running_suspect flag — loose, likely trend-continuation capture; treat as unreliable.

## 3. Sample sizes (research XAUUSD)
- A: D1 12 diag / 6 conv; H1 13 / 3. Validation: D1 n=1, H1 n=2 (starved).
- B: D1 contracting 4, barrier 24, expanding 2, running_suspect 119; H1 1 / 52 / 8 / 102.
- F: D1 510–793 per prefix; H1 649–986.
- G: D1 1222 Elliott / 1068 generic; H1 1509 / 1445.

## 4. Predictive statistics (research)
- A reversal expectancy: D1 +0.25R [-0.50,+1.00]; H1 -0.39R [-0.91,+0.26]. Winrate vs converging null p=0.74/1.00.
- B breakout direction accuracy: contracting 25%/0%, barrier 73%/74%, expanding 0%/100%, running 68%/79%; median mag 0.9–3.5 ATR. Descriptive only (see 5).
- F median |5-bar| move: 1.33–1.38 ATR (D1), 0.79–0.83 ATR (H1) — no differentiation across prefix kinds; directional prediction not tested.
- G reversal: Elliott 39.4%/33.8% vs generic 39.4%/35.4%, p=0.98/0.39.

## 5. Null-model comparison
- A: diagonal vs generic-converging null — no difference (q=1.0). Diagonal label adds nothing beyond "converging structure".
- B: NO randomized-triangle control was run — barrier/running accuracy cannot be distinguished from trend-continuation base rate. Not evidence.
- G: Elliott invalidation == generic swing failure. No incremental info.

## 6. Incremental information gain
- Formal Models A–E (E2-N) not run this batch; proxy: Elliott candidates vs trend/breakout baselines on validation — trend D1 -0.15/H1 -0.03R; breakout D1 -0.30/H1 +0.14R; Elliott A validation D1 -1.0/H1 -0.63R. No gain demonstrated.

## 7. Validation results
- A_diag: D1 -1.00R (n=1), H1 -0.63R [-1.00,-0.25] (n=2). Negative; starved.
- G_inv reversal: D1 40% (n=65), H1 36% (n=306) — matches research null rates, no control separation.
- B/F validation of outcomes not preregistered this batch — not run (gap logged, not a claim).

## 8. Robustness
- No parameter sweep launched (would be unjustified on null/starved results). Costs: prior E1 sweeps stable but irrelevant here.

## 9. Count sensitivity
- Overlapping impulse/triangle windows share swings; best-vs-average count analysis not run. Any future barrier-triangle claim must be flagged COUNT-SENSITIVE until tested (E2-M outstanding).

## 10. Multiple-testing results
- Family p: [0.74, 0.98, 1.00, 0.39]; BH-FDR q all 1.00. Zero significant. No cherry-picking; full family recorded in reports/elliott_e2abfg.json and registry.

## 11. Surviving hypotheses
- NONE. Nothing meets E2-T (causal yes; sample A/B-starved; prediction null; no gain; validation failed; counting risk open).

## 12. Rejected hypotheses
- A: diagonal reversal edge — REJECTED (null + validation negative).
- B: triangle breakout edge — INSUFFICIENT EVIDENCE (descriptive accuracy without null/validation; do not trade).
- F: partial-prefix differential info — NOT SUPPORTED as tested (absolute-move only, no directional separation).
- G: Elliott-specific invalidation edge — REJECTED (== generic failure).

## Decision
STOP per spec. No candidate presented for freezing. No final OOS. Remaining E2 (C/D/E/H/I/J/K/L/M/N/O/P second half) NOT launched — requires approval + new preregistration. E1 remains closed and unmodified.

## PART 2 — Second half (C/D/E/H/I/J/K/L/M/N/O/P), prereg E2-2ND-001, no final OOS
M30/M15 unavailable (Yahoo 1h floor); D/E use D1/H4/H1.

1. Tested: C adjacent-ABC clustering; H ext ratios vs lognormal; I alternation + W5 AUC; J channel distance; K symmetries; L internal sub-swing split; D/E D1×H1/H4 nesting; M overlapping-count flips; N Models A–E AUC/Brier/logloss; O surrogate (C + E1); P trend/breakout baselines.
2. Non-detectable: C double/triple/W-X-Y — CORRECTED to NOT RELIABLY DETECTABLE (adjacent counts 625/749 vs surr ~100 are window-overlap artifacts; no X-connector definition). L split degenerate (61/0, 64/2) — design untestable. M keying found 0 regions — method gap, not stability proof.
3. Samples: H n=61/66; I n=61/66; J n=61/66; K imp 61/66 abc 793/986; DE H1 38/28, H4 12/7; N rows ~8k/1.7k bars.
4. Predictive: H hit 21%/26% BELOW chance 28%/27% (p=0.91/0.65). I Wilcoxon p=0.80/0.64; W5 AUC 0.51/0.64 (H1 exploratory, n=66, no validation). K all p>0.05 (min 0.068). DE aligned-conflicting gaps n.s. (p=0.43/1.0). L n.s.
5. Nulls: H loses to lognormal; C surplus artifactual; J no null (descriptive 0.75/0.89 ATR).
6. Information gain (central N, validation AUC): A 0.508, B 0.506, C 0.508, D 0.516, E 0.506. Elliott (C) == structure alone (A); full stack (E) == baseline. Brier/logloss flat. Answer: NO — Elliott adds nothing.
7. Validation: impulse continuation D1 -0.40 (n=4), H1 -0.12 (n=13). N above. Nothing replicates.
8. Robustness: unjustified on nulls; not run.
9. Count sensitivity: untested due to method gap — any future claim defaults to COUNT-SENSITIVE.
10. Multiple testing: 12 p-values, all BH-q ≥ 0.62. Zero significant.
11. Surviving: NONE.
12. Rejected: C (artifactual), H, I, J (descriptive), K, L (design), D/E (n.s.), M (gap), N (definitive no-gain), O supports null.

DECISION: STOP. No freeze, no final OOS. E2 family closed. Overall Elliott verdict: NOT SUPPORTED.
