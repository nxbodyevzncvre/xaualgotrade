"""Download free XAUUSD (GC=F proxy) via yfinance; save raw + splits. Decisions logged."""
import json, sys
from pathlib import Path
import pandas as pd
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.adapter import save_raw
from data.quality import quality_report
from validation.splits import chrono_split

CFG = json.load(open(ROOT / "configs" / "config.json"))
SYM = "XAUUSD"
TICKER = CFG["yahoo_map"][SYM]

def dl(ticker, period, interval):
    import yfinance as yf
    df = yf.download(ticker, period=period, interval=interval, auto_adjust=False,
                     progress=False, threads=False)
    if df is None or len(df) == 0:
        return None
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0].lower() for c in df.columns]
    else:
        df.columns = [c.lower() for c in df.columns]
    df = df.reset_index()
    col = "datetime" if "datetime" in df.columns else ("date" if "date" in df.columns else df.columns[0])
    out = pd.DataFrame({"timestamp": pd.to_datetime(df[col], utc=True),
                        "open": df["open"], "high": df["high"],
                        "low": df["low"], "close": df["close"],
                        "tick_volume": df.get("volume", 0)})
    return out.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)

def main():
    jobs = [("D1", "max", "1d"), ("H1", "2y", "1h"), ("H4", "2y", "1h")]
    saved = {}
    for tf, per, iv in jobs:
        print(f"Downloading {SYM} {tf} ({TICKER} {per}/{iv}) ...", flush=True)
        try:
            df = dl(TICKER, per, iv)
        except Exception as e:
            print(f"  FAIL: {e}")
            continue
        if df is None or len(df) == 0:
            print("  EMPTY")
            continue
        if tf == "H4":
            df = df.set_index("timestamp").resample("4h").agg(
                {"open": "first", "high": "max", "low": "min", "close": "last",
                 "tick_volume": "sum"}).dropna().reset_index()
        path = save_raw(df, SYM, tf, "yahoo", {"ticker": TICKER, "period": per, "interval": iv})
        print(f"  saved {path} rows={len(df)} {df.timestamp.iloc[0]} -> {df.timestamp.iloc[-1]}")
        print("  quality:", json.dumps(quality_report(df), indent=1))
        saved[tf] = str(path)
    # split primary H1 (or D1 fallback) into research/validation/final
    base = None
    for tf in ["H1", "D1", "H4"]:
        c = ROOT / "data" / "raw" / f"{SYM}_{tf}_yahoo.csv"
        if c.exists():
            base = (tf, pd.read_csv(c, parse_dates=["timestamp"]))
            break
    if base:
        tf, df = base
        df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
        r, v, f = chrono_split(df, CFG["data_split"]["research"], CFG["data_split"]["validation"])
        for name, d in [("research_data", r), ("validation_data", v), ("final_test_data", f)]:
            (ROOT / name).mkdir(exist_ok=True)
            d.to_csv(ROOT / name / f"{SYM}_{tf}.csv", index=False)
        print(f"SPLIT {tf}: research={len(r)} validation={len(v)} final={len(f)}")
        print(json.dumps({"split_source": tf, "research": [str(r.timestamp.iloc[0]), str(r.timestamp.iloc[-1])],
                          "validation": [str(v.timestamp.iloc[0]), str(v.timestamp.iloc[-1])],
                          "final": [str(f.timestamp.iloc[0]), str(f.timestamp.iloc[-1])]}, indent=1))

if __name__ == "__main__":
    main()
