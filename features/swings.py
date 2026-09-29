"""Causal swing detection. Confirmation timestamp = signal timestamp (no look-ahead)."""
import pandas as pd
import numpy as np

def fractal_swings(df: pd.DataFrame, k: int = 2) -> pd.DataFrame:
    """Pivot high/low confirmed with k bars on each side. confirm_idx = i+k."""
    out = []
    h, l = df.high.values, df.low.values
    n = len(df)
    for i in range(k, n - k):
        if h[i] == max(h[i-k:i+k+1]):
            out.append({"confirm_idx": i + k, "swing_idx": i, "price": float(h[i]),
                        "type": "high", "timestamp": df.timestamp.iloc[i+k]})
        if l[i] == min(l[i-k:i+k+1]):
            out.append({"confirm_idx": i + k, "swing_idx": i, "price": float(l[i]),
                        "type": "low", "timestamp": df.timestamp.iloc[i+k]})
    return pd.DataFrame(out)

def atr_pivots(df: pd.DataFrame, atr_period: int = 14, mult: float = 1.0) -> pd.DataFrame:
    """Volatility-adjusted swings: fractal with threshold ATR*mult from last swing."""
    tr = pd.concat([df.high - df.low, (df.high - df.close.shift(1)).abs(),
                    (df.low - df.close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.rolling(atr_period).mean().bfill().values
    k = 2
    out, last_price, last_type = [], None, None
    h, l = df.high.values, df.low.values
    n = len(df)
    for i in range(k, n - k):
        is_h = h[i] == max(h[i-k:i+k+1])
        is_l = l[i] == min(l[i-k:i+k+1])
        th = atr[i] * mult
        if is_h and (last_price is None or abs(h[i]-last_price) >= th or last_type == "low"):
            if last_type != "high":
                out.append({"confirm_idx": i+k, "swing_idx": i, "price": float(h[i]), "type": "high",
                            "timestamp": df.timestamp.iloc[i+k]})
                last_price, last_type = float(h[i]), "high"
        if is_l and (last_price is None or abs(l[i]-last_price) >= th or last_type == "high"):
            if last_type != "low":
                out.append({"confirm_idx": i+k, "swing_idx": i, "price": float(l[i]), "type": "low",
                            "timestamp": df.timestamp.iloc[i+k]})
                last_price, last_type = float(l[i]), "low"
    return pd.DataFrame(out)

def zigzag_swings(df: pd.DataFrame, pct: float = 0.005) -> pd.DataFrame:
    """Causal percentage zigzag on close. Lags by design; confirm = bar where threshold crossed."""
    c = df.close.values
    n = len(df)
    out = []
    anchor_idx, anchor_px, direction = 0, c[0], 0
    for i in range(1, n):
        chg = (c[i]-anchor_px)/anchor_px
        if direction >= 0 and chg <= -pct:
            out.append({"confirm_idx": i, "swing_idx": int(np.argmax(c[anchor_idx:i+1])+anchor_idx),
                        "price": float(np.max(c[anchor_idx:i+1])), "type": "high",
                        "timestamp": df.timestamp.iloc[i]})
            anchor_idx, anchor_px, direction = int(np.argmin(c[anchor_idx:i+1])+anchor_idx), float(np.min(c[anchor_idx:i+1])), -1
        elif direction <= 0 and chg >= pct:
            if direction == -1:
                out.append({"confirm_idx": i, "swing_idx": anchor_idx, "price": float(anchor_px),
                            "type": "low", "timestamp": df.timestamp.iloc[i]})
            anchor_idx, anchor_px, direction = int(np.argmax(c[anchor_idx:i+1])+anchor_idx), float(np.max(c[anchor_idx:i+1])), 1
    return pd.DataFrame(out)
