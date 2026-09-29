"""Standardized OHLC adapter. Raw immutable; processed logged."""
import pandas as pd
from pathlib import Path

RAW = Path(__file__).resolve().parents[1] / "data" / "raw"
META = Path(__file__).resolve().parents[1] / "data" / "metadata"

REQUIRED = ["timestamp", "open", "high", "low", "close"]

def standardize(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.sort_values("timestamp").drop_duplicates("timestamp", keep="first").reset_index(drop=True)
    for c in ["open", "high", "low", "close"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    return df[REQUIRED + [c for c in ["tick_volume", "spread"] if c in df.columns]]

def save_raw(df: pd.DataFrame, symbol: str, timeframe: str, source: str, meta: dict):
    RAW.mkdir(parents=True, exist_ok=True)
    META.mkdir(parents=True, exist_ok=True)
    df = standardize(df)
    path = RAW / f"{symbol}_{timeframe}_{source}.csv"
    df.to_csv(path, index=False)
    import json, time
    with open(META / f"{symbol}_{timeframe}_{source}.json", "w") as f:
        json.dump({"symbol": symbol, "timeframe": timeframe, "source": source,
                   "download_ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "rows": len(df), "start": str(df.timestamp.iloc[0]), "end": str(df.timestamp.iloc[-1]),
                   **meta}, f, indent=2)
    return path

def load_raw(symbol: str, timeframe: str, source: str) -> pd.DataFrame:
    path = RAW / f"{symbol}_{timeframe}_{source}.csv"
    df = pd.read_csv(path, parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    return df
