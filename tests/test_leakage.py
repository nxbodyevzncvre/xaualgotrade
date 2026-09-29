"""Leakage tests: every microstructure feature at t must equal recomputation on data<=t."""
import pandas as pd
import numpy as np
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import microstructure as MS

def _m1(n=3000):
    rng = np.random.default_rng(0)
    ts = pd.date_range("2021-03-01", periods=n, freq="min", tz="UTC")
    c = 1800 + rng.normal(0, 1, n).cumsum()
    return pd.DataFrame({"timestamp": ts, "open": c, "high": c+0.3, "low": c-0.3, "close": c+0.05})

def test_m5_uses_no_future():
    m1 = _m1()
    a = MS.m5_frame(m1)
    b = MS.m5_frame(m1.iloc[:1500])
    Assert = len(a) > len(b)
    assert Assert
    pd.testing.assert_frame_equal(a.iloc[:len(b)][["open","high","low","close"]],
                                  b[["open","high","low","close"]])

def test_order_causal():
    m1 = _m1()
    full = MS.f3_order(m1).iloc[2000]
    part = MS.f3_order(m1.iloc[:2001]).iloc[-1]
    assert full == part

def test_efficiency_causal():
    m1 = _m1()
    full = MS.efficiency(m1.close, 60).iloc[2000]
    part = MS.efficiency(m1.close.iloc[:2001], 60).iloc[-1]
    assert abs(full-part) < 1e-12

def test_f2_formation_causal():
    m1 = _m1(n=5000)
    f2 = MS.f2_formation(m1)
    assert len(f2) > 0
    # range_frac at 15-min decision must be reproducible from data <= decision ts
    row = f2[f2.mins == 15].iloc[0]
    ts = row.ts
    sub = m1[m1.timestamp <= ts]
    seg_start = ts.replace(minute=0, second=0)
    seg = sub[sub.timestamp >= seg_start]
    a = (seg.high-seg.low).rolling(14, min_periods=5).mean().iloc[-1]
    rg = (seg.high.max()-seg.low.min())/a
    assert abs(rg-row.range_frac) < 1e-9

def test_session_rule_documented():
    import inspect
    src = inspect.getsource(MS.session_filter)
    assert "weekday" in src and "< 5" in src
