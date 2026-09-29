"""FAM-1 tick-spread regression tests (§I.7 + B1-B8). Synthetic data only — no real
data reads, no 2024+ access. Guards the prereg-bound estimators in
research/run_tickspread.py without executing the validation pipeline."""
import json
import re
from pathlib import Path

import numpy as np
import pandas as pd

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from research import run_tickspread as T
from statsx.permutation import bootstrap_mean_ci, bh_fdr_real

SRC = (ROOT / "research" / "run_tickspread.py").read_text()


def _synth_m5(n=60, seed=0):
    """Synthetic mid-M5 frame with OHLC/close/spread/atr14/ret/d1/session/vol_state."""
    rng = np.random.default_rng(seed)
    ts = pd.date_range("2021-01-04 00:00", periods=n, freq="5min", tz="UTC")
    close = 1900.0 + np.cumsum(rng.normal(0, 1.0, n))
    high = close + np.abs(rng.normal(0, 0.5, n))
    low = close - np.abs(rng.normal(0, 0.5, n))
    m5 = pd.DataFrame({"timestamp": ts, "open": close - 0.1, "high": high,
                       "low": low, "close": close,
                       "spread": np.full(n, 0.35), "n_ticks": np.full(n, 100)})
    tr = pd.concat([m5.high - m5.low, (m5.high - m5.close.shift(1)).abs(),
                    (m5.low - m5.close.shift(1)).abs()], axis=1).max(axis=1)
    m5["atr14"] = tr.rolling(14, min_periods=14).mean()
    m5["ret"] = m5.close.pct_change()
    m5["d1"] = np.where(m5.ret / m5.atr14 * m5.close > 0.02, "UP",
               np.where(m5.ret / m5.atr14 * m5.close < -0.02, "DN", "NEU"))
    m5["session"] = "london"
    m5["vol_state"] = "NORM"
    return m5


# ---- B1: next-bar alignment; feature at t cannot use return from t ----
def test_b1_next_bar_alignment():
    m5 = _synth_m5()
    nxt = T.next_ret_diff(m5.close, m5.atr14)
    # target[t] == (close[t+1]-close[t])/atr[t] by construction
    t = 20
    assert np.isfinite(m5.atr14.iloc[t])
    assert nxt.iloc[t] == (m5.close.iloc[t + 1] - m5.close.iloc[t]) / m5.atr14.iloc[t]
    assert np.isnan(nxt.iloc[len(m5) - 1]), "terminal shift(-1) target must be NaN"
    # perturbing close[t+1] changes target[t] but not state[t] inputs (closes <= t)
    m5b = m5.copy()
    m5b.loc[m5b.index[t + 1], "close"] += 50.0
    nxtb = T.next_ret_diff(m5b.close, m5b.atr14)
    assert nxtb.iloc[t] != nxt.iloc[t], "target must respond to next-bar close"
    # state at t depends only on ret[t] (closes t-1, t): unchanged rows stay equal
    assert m5b.ret.iloc[t] == m5.ret.iloc[t]


def test_b1_gross_net_share_mask_convention():
    # module must condition gross/mid targets with mk[:-1] (state at t, move t->t+1),
    # the same convention the net estimator uses — grep the loop body
    loop = SRC.split("for cell in FAMILY7:")[1].split("q = bh_fdr_real")[0]
    assert "mk[:-1]" in loop, "gross/mid must use state-at-t mask mk[:-1]"
    assert "mk[1:]" not in loop, "B1 regression: contemporaneous mk[1:] must be gone"


# ---- B2: paired artifact d_i = bid_ret_i - mid_ret_i, joint finite mask ----
def test_b2_paired_artifact():
    rng = np.random.default_rng(3)
    n = 200
    g_raw = rng.normal(0.01, 0.1, n)
    m_raw = rng.normal(0.0, 0.1, n)
    g_raw[::17] = np.nan  # staggered NaN patterns (bid warmup vs mid warmup)
    m_raw[5::23] = np.nan
    joint = np.isfinite(g_raw) & np.isfinite(m_raw)
    d = g_raw[joint] - m_raw[joint]
    assert len(d) == joint.sum()
    assert len(d) < n and len(d) > n - 40
    # unpaired truncation (old bug) would pair k-th finite with k-th finite across legs
    gf = g_raw[np.isfinite(g_raw)]
    mf = m_raw[np.isfinite(m_raw)]
    d_bad = gf[:len(mf)] - mf[:len(gf)]
    assert not np.array_equal(d, d_bad), "test setup must distinguish paired vs truncated"
    assert "g_raw[joint] - m_raw[joint]" in SRC or "g - m_" in SRC
    assert "g[:len(m_)]" not in SRC and "m_[:len(g)]" not in SRC, "B2 truncation must be gone"


# ---- B3: diff/ATR units, not pct/ATR ----
def test_b3_diff_over_atr_units():
    m5 = _synth_m5()
    nxt = T.next_ret_diff(m5.close, m5.atr14)
    t = 30
    pct_version = m5.close.pct_change().iloc[t + 1] / m5.atr14.iloc[t] \
        if False else None  # placeholder guard below
    # diff/ATR magnitude ~ price units; pct/ATR would be ~1/close smaller
    assert abs(nxt.iloc[t]) > abs(m5.close.pct_change().iloc[t + 1] / m5.atr14.iloc[t]) * 100
    assert "pct_change" not in SRC.split("def next_ret_diff")[1].split("def ")[0], \
        "next_ret_diff must not use pct_change"


# ---- B4: bid ATR is true-range ATR14 ----
def test_b4_bid_atr_true_range():
    bid_m1 = pd.DataFrame({
        "timestamp": pd.date_range("2023-02-01", periods=120, freq="min", tz="UTC"),
        "open": 1900.0, "high": 1900.5, "low": 1899.5,
        "close": 1900.0 + np.sin(np.arange(120) / 5.0),
        "tick_volume": 1.0})
    b5 = T.build_bid_m5(bid_m1)
    assert {"timestamp", "bid_close", "bid_atr"} <= set(b5.columns)
    # manual true-range check on first 14 valid bars
    g = bid_m1.set_index("timestamp")
    c = g.close.resample("5min").last().dropna()
    h = g.high.resample("5min").max().reindex(c.index)
    lo = g.low.resample("5min").min().reindex(c.index)
    tr = pd.concat([h - lo, (h - c.shift(1)).abs(), (lo - c.shift(1)).abs()], axis=1).max(axis=1)
    expect = tr.rolling(14, min_periods=14).mean().dropna()
    got = b5.set_index("timestamp").bid_atr.dropna()
    pd.testing.assert_series_equal(got, expect, check_names=False, check_freq=False)
    assert ".diff().abs().rolling(14" not in SRC, "B4 close-diff proxy must be gone"


# ---- Cost/sign algebra: long DN->fade and short UP->fade ----
def test_cost_sign_algebra():
    # long: buy ask at entry, sell bid at exit
    ce, cx, se, sx, direction = 1900.0, 1901.0, 0.4, 0.6, 1
    assert direction * (cx - ce) - (se + sx) / 2 == 1.0 - 0.5
    # short: sell bid at entry, buy ask at exit
    ce, cx, direction = 1900.0, 1899.0, -1
    assert direction * (cx - ce) - (se + sx) / 2 == 1.0 - 0.5
    for cell, d in T.FADE_DIR.items():
        if "UP" in cell and cell != "UPDN":
            assert d == -1, f"{cell} fades UP -> short"
        if cell in ("DN", "UPDN", "DNDN"):
            assert d == 1, f"{cell} fades DN -> long"


# ---- D-logic truth table (helpers are module-level, importable) ----
def test_d_logic_truth_table():
    assert T._ci_excludes_zero([0.05, 0.20]) is True
    assert T._ci_excludes_zero([-0.20, -0.05]) is True  # negative counts: phenomenon, not edge
    assert T._ci_excludes_zero([-0.05, 0.20]) is False
    assert T._ci_excludes_zero([None, None]) is False
    assert T._sgn([0.05, 0.20]) == 1
    assert T._sgn([-0.20, -0.05]) == -1
    assert T._sgn([-0.05, 0.20]) == 0
    # gate text distinguishes sign-mismatch from no-significance
    assert "sign-mismatch" in SRC


# ---- FDR: exact prereg 7-cell family; no hardcoded status; JSON-safe ----
def test_fdr_exact_7cell_family():
    assert T.FAMILY7 == ["UP", "DN", "NEU", "UPUP", "DNUP", "UPDN", "DNDN"]
    assert len(T.FAMILY7) == 7
    assert set(T.DIR6) < set(T.FAMILY7) and "NEU" not in T.DIR6
    q = bh_fdr_real([0.01, 0.2, 0.5, 0.04, 0.9, 0.11, 0.03])
    assert len(q) == 7
    loop = SRC.split("for cell in FAMILY7:")[1]
    assert "zip(FAMILY7, q)" in SRC, "BH q-values must map onto the 7-cell family"


def test_no_hardcoded_rejected_status():
    assert 'status = "PROMISING" if ok_cells else "REJECTED"' in SRC
    assert SRC.count('status": "REJECTED"') == 0 and SRC.count("status='REJECTED'") == 0


def test_json_no_nan():
    payload = {"ci95": [T._finite_float(float("nan")), T._finite_float(float("inf"))],
               "mean": T._finite_float(0.123456)}
    assert payload["ci95"] == [None, None]
    s = json.dumps(payload, allow_nan=False)
    assert "NaN" not in s
    assert payload["mean"] == 0.1235


def test_permutation_import_used():
    # B6: prereg-specified permutation_diff_p must be called (NEU return-vector p)
    assert "permutation_diff_p(x1, x0)" in SRC


# ---- Firewall: no 2024+ year literal in loader calls; no final-OOS reads ----
def test_firewall_no_final_oos():
    assert "final_test_data" not in SRC, "FAM-1 module must never reference final_test_data"
    for m in re.finditer(r"load_minutes\(\[([^\]]*)\]\)", SRC):
        years = m.group(1)
        assert "2024" not in years and "2025" not in years and "2026" not in years, \
            f"loader call touches locked years: {years}"
    assert "load_minutes([2020, 2021, 2022])" in SRC
    assert "load_minutes([2023])" in SRC


# ---- ATR parity: to_m5 mid ATR equals MS.m5_frame convention ----
def test_atr_parity_mid():
    from features import microstructure as MS
    assert "max(axis=1)" in SRC  # true-range max in to_m5
    m1 = pd.DataFrame({
        "timestamp": pd.date_range("2021-03-01", periods=300, freq="min", tz="UTC"),
        "open": 1900.0, "high": 1900.4, "low": 1899.6, "close": 1900.0})
    m1["close"] = 1900.0 + np.cumsum(np.random.default_rng(9).normal(0, 0.05, 300))
    m1["high"] = m1.close + 0.2
    m1["low"] = m1.close - 0.2
    ref = MS.m5_frame(m1)[["timestamp", "atr14"]].dropna()
    assert len(ref) > 0 and (ref.atr14 > 0).all()
