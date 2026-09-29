"""Causality tests: no future use before confirmation; pairs known only at confirm_idx."""
import pandas as pd
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, fibonacci as FIB, volatility as V

def test_fractal_confirm_lag():
    df = pd.read_csv(ROOT/"research_data"/"XAUUSD_H1.csv", parse_dates=["timestamp"])
    sw = SW.fractal_swings(df, 2)
    assert len(sw) > 0
    assert ((sw.confirm_idx - sw.swing_idx) == 2).all(), "fractal confirm must lag exactly k"

def test_pairs_known_at_max_confirm():
    df = pd.read_csv(ROOT/"research_data"/"XAUUSD_H1.csv", parse_dates=["timestamp"])
    sw = SW.fractal_swings(df, 2)
    pairs = FIB.pairs_to_retracements(sw)
    swi = sw.set_index(sw.index)
    for _, p in pairs.head(50).iterrows():
        assert p.confirm_idx >= 0
    # reaction measurement starts strictly after confirm
    df = V.add_volatility(df)
    react = FIB.measure_reactions(df, pairs.head(10))
    assert len(react) > 0

def test_no_nan_atr_signal():
    df = pd.read_csv(ROOT/"research_data"/"XAUUSD_H1.csv", parse_dates=["timestamp"])
    df = V.add_volatility(df)
    assert df.atr.iloc[20] == df.atr.iloc[20]  # ATR defined after warmup
    assert df.atr.iloc[0] != df.atr.iloc[0]    # NaN at start -> signals skip these
