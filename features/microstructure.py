"""M1 microstructure features. Vectorized, causal (rolling/min_periods, shifts).
Session rule R5-SESSION-001: keep Mon-Fri (weekday<5, UTC); Sat/Sun dropped for research only.
Raw files immutable. Identical rule all splits. Not optimized."""
import pandas as pd
import numpy as np

def session_filter(df):
    df = df.copy()
    wd = pd.to_datetime(df.timestamp).dt.weekday
    return df[wd < 5].reset_index(drop=True)

def add_sessions(df):
    h = pd.to_datetime(df.timestamp).dt.hour
    df = df.copy()
    df["session"] = np.where(h < 7, "asian", np.where(h < 12, "london", np.where(h < 17, "ny", "off")))
    df["tod"] = h
    return df

def m5_frame(m1):
    g = m1.set_index("timestamp")
    o = g.open.resample("5min").first(); h = g.high.resample("5min").max()
    l = g.low.resample("5min").min(); c = g.close.resample("5min").last()
    m5 = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna().reset_index()
    m5 = add_sessions(m5)
    tr = pd.concat([m5.high-m5.low, (m5.high-m5.close.shift(1)).abs(),
                    (m5.low-m5.close.shift(1)).abs()], axis=1).max(axis=1)
    m5["atr14"] = tr.rolling(14, min_periods=14).mean()
    m5["ret"] = m5.close.pct_change()
    m5["range"] = m5.high-m5.low
    m5["rv_state"] = m5.ret.rolling(240, min_periods=240).std()
    m5["vol_state"] = m5.rv_state.rolling(2000, min_periods=2000).rank(pct=True)
    m5["vol_state"] = pd.cut(m5.vol_state, [0, .33, .66, 1.0], labels=["LOW", "NORM", "HIGH"])
    return m5

def f1_path(m1, m5):
    """Completed-M5 path class from M1 subdivision. Decision at M5 close; uses only bars < close."""
    m1i = m1.set_index("timestamp")
    cls, cloc = [], []
    for ts in m5.timestamp:
        seg = m1i.loc[ts-pd.Timedelta(minutes=5):ts-pd.Timedelta(minutes=1)]
        if len(seg) == 0:
            cls.append("NA"); cloc.append(np.nan); continue
        hi = seg.high.values.argmax(); lo = seg.low.values.argmin()
        cls.append("OHLC" if hi < lo else "OLHC")
        rg = seg.high.max()-seg.low.min()
        cloc.append((seg.close.iloc[-1]-seg.open.iloc[0])/rg if rg > 0 else 0.0)
    m5 = m5.copy()
    m5["path"] = cls
    m5["close_loc"] = pd.cut(cloc, [-np.inf, 1/3, 2/3, np.inf], labels=["lo", "mid", "hi"])
    return m5

def f2_formation(m1):
    """H1 formation at +15/+30/+45 min: range-so-far and displacement-so-far / M5-ATR proxy.
    Returns rows per H1 window with decision ts. Causal: uses only bars <= decision."""
    g = m1.set_index("timestamp")
    rows = []
    for hstart, seg in g.groupby(pd.Grouper(freq="h")):
        seg = seg.between_time("00:00", "23:59")
        if len(seg) < 50:
            continue
        o0 = seg.open.iloc[0]
        a_full = (seg.high-seg.low).rolling(14, min_periods=5).mean()
        for m in [15, 30, 45]:
            sub = seg.iloc[:m]
            a = a_full.iloc[m-1]  # causal: only bars <= decision
            if not np.isfinite(a) or a <= 0:
                continue
            rg = sub.high.max()-sub.low.min()
            rows.append({"ts": seg.index[m-1], "mins": m, "range_frac": rg/a,
                         "disp": (sub.close.iloc[-1]-o0)/a,
                         "rest_ret": (seg.close.iloc[-1]-sub.close.iloc[-1])/a})
    return pd.DataFrame(rows)

def f3_order(m1, window=60):
    """High-first vs low-first in trailing window. Decision at each M1 bar (subsampled later)."""
    h = m1.high.rolling(window, min_periods=window).apply(lambda x: int(np.argmax(x)), raw=True)
    l = m1.low.rolling(window, min_periods=window).apply(lambda x: int(np.argmin(x)), raw=True)
    return pd.Series(np.where(h < l, "HF", "LF"), index=m1.index)

def efficiency(close, window):
    net = (close-close.shift(window)).abs()
    path = close.diff().abs().rolling(window, min_periods=window).sum()
    return net/(path+1e-12)
