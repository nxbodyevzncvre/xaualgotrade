"""Data quality checks. Never silently repair; report only."""
import pandas as pd

def quality_report(df: pd.DataFrame) -> dict:
    r = {}
    r["rows"] = len(df)
    r["start"] = str(df.timestamp.iloc[0]) if len(df) else None
    r["end"] = str(df.timestamp.iloc[-1]) if len(df) else None
    r["duplicate_timestamps"] = int(df.duplicated("timestamp").sum())
    d = df.sort_values("timestamp")
    deltas = d.timestamp.diff().dropna()
    r["median_delta"] = str(deltas.median()) if len(deltas) else None
    # impossible OHLC
    bad = ((d.high < d[["open", "close"]].max(axis=1)) | (d.low > d[["open", "close"]].min(axis=1))).sum()
    r["impossible_ohlc"] = int(bad)
    # gaps: delta > 3x median
    med = deltas.median()
    r["gaps_gt3x_median"] = int((deltas > 3 * med).sum()) if len(deltas) else 0
    # zero / negative prices
    r["nonpositive_prices"] = int(((d[["open", "high", "low", "close"]] <= 0).any(axis=1)).sum())
    # weekend bars (Sat/Sun)
    wd = d.timestamp.dt.weekday
    r["weekend_bars"] = int(((wd == 5) | (wd == 6)).sum())
    # extreme returns: |logret| > 5%
    lr = (d.close / d.close.shift(1)).apply(lambda x: abs(x - 1) if x == x else 0)
    r["extreme_moves_gt5pct"] = int((lr > 0.05).sum())
    r["missing_values"] = int(d[["open", "high", "low", "close"]].isna().sum().sum())
    return r
