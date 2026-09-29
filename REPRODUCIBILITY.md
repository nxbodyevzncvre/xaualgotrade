# Reproducibility manifest
- Seed: 42 (reaction controls seed 42, MC seed 42, session sample seed 42).
- Data: GC=F/SI=F/PL=F/PA=F via yfinance; raw CSVs in data/raw + metadata JSON; splits 70/15/15 H1, date-based D1 (<2023 / 2023 / >=2024).
- Registry: research/experiments/registry.jsonl (append-only).
- Frozen: final_test/strategy_freeze.json v1.0.0-frozen; final run once via final_test/final_evaluator.py (no feedback).
- Tests: tests/test_causality.py (3 passed).
- Stack: venv .venv (numpy, pandas, matplotlib, scipy, statsmodels, scikit-learn, pyarrow, pytest, yfinance).
- Code: single-session authoring, no git history (add git init to version from here).
