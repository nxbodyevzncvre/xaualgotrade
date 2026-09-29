"""ATR + volatility regimes; entropy/Hurst kept minimal for Phase 1."""
import pandas as pd
import numpy as np

def atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    tr = pd.concat([df.high-df.low, (df.high-df.close.shift(1)).abs(),
                    (df.low-df.close.shift(1)).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def add_volatility(df: pd.DataFrame, period: int = 14, pct_window: int = 200) -> pd.DataFrame:
    df = df.copy()
    df["atr"] = atr(df, period)
    df["atr_pct"] = df.atr.rolling(pct_window).rank(pct=True)
    df["vol_regime"] = pd.cut(df.atr_pct, [0, 0.33, 0.66, 1.0], labels=["low", "mid", "high"])
    df["rv"] = df.close.pct_change().rolling(period).std() * np.sqrt(period)
    return df

def hurst(ts: np.ndarray, max_lag: int = 50) -> float:
    ts = np.asarray(ts, dtype=float)
    if len(ts) < max_lag + 10:
        return float("nan")
    lags = range(2, max_lag)
    tau = [np.std(ts[l:] - ts[:-l]) for l in lags]
    try:
        return float(np.polyfit(np.log(list(lags)), np.log(tau), 1)[0])
    except Exception:
        return float("nan")
