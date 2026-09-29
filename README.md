# quant-research-xauusd — algos on Gold (XAUUSD / GC=F)

Systematic research of intraday/swing algos on Gold: Fibonacci + swings + volatility regime, with strict validation.

> Status: research / INSUFFICIENT EVIDENCE for frozen strategy `FIB-H1-05-HIVOL-001` v1.0.0-frozen — validation CI crosses 0, D1 fails. See `strategy_freeze.json` + `REPRODUCIBILITY.md`.

## Structure
- `configs/config.json` — symbol map (XAUUSD → GC=F), TFs, costs, fib/swing/risk params
- `data/` — loaders (`download.py`, `download_duk.py`, `dl_tick.py`, `adapter.py`, `quality.py`). Raw tick/M1 caches excluded from git (see below)
- `features/` — swings, fibonacci, volatility, microstructure, structure, elliott
- `backtesting/engine.py` — Fixed-R backtest (entry at signal close, SL/TP in R, time-stop, costs)
- `research/` — run_phase1/2, run_round3/4/5, elliott, validation, registry (`research/experiments/registry.jsonl`)
- `validation/`, `final_test/final_evaluator.py` — walk-forward / blind test (run once, no feedback)
- `statsx/` — permutation tests, multiple-testing corrections
- `tests/` — `test_causality.py`, `test_leakage.py`, `test_stats.py`
- `reports/`, `visualization/` — figures
- `strategy_freeze.json` — frozen candidate

## Repro
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
pytest -q
python research/run_phase1.py
```

Seed: 42 everywhere. Splits: 70/15/15 chronological (H1), D1 by date (<2023 / 2023 / >=2024).

## Data — why not in git
GitHub rejects files >100MB and repos >5GB. This project generates ~6GB:
- `data/raw/_tickcache/` ~5.8GB, `_dukcache/` ~191MB, `_tickagg/` ~77MB
- `data/raw/XAUUSD_M1_dukascopy.csv` ~159MB

They are git-ignored by design. Regenerate locally:
```bash
python data/download.py        # yfinance: GC=F, H1/D1
python data/download_duk.py    # Dukascopy M1/M5
python data/dl_tick.py         # tick cache
```
Small H1/D1 CSVs are tracked; M1/M5 and `*.pkl/*.parquet` are not.

## Strategy (frozen, not live-ready)
`FIB-H1-05-HIVOL-001`: fractal swings k=2, fade fib 0.5, ATR14 high-vol regime only, SL 1.5×ATR, TP 2R, max hold 20 bars. Costs: spread 0.35 + slippage 0.15.
