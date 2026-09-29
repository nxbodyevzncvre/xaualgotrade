"""Tick download: monthly chunks -> per-minute aggregates (mid_close, spread stats, counts).
Raw ticks kept in _tickcache for audit. Allowed window ONLY 2020-01-01..2023-12-31. NEVER 2024+."""
import sys, time
from pathlib import Path
import pandas as pd, datetime
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT/"data"/"raw"/"_tickcache"; CACHE.mkdir(parents=True, exist_ok=True)
AGG = ROOT/"data"/"raw"/"_tickagg"; AGG.mkdir(parents=True, exist_ok=True)
from dukascopy_python import fetch, INTERVAL_TICK, OFFER_SIDE_BID

def one_month(y, m):
    key = CACHE/f"tick_{y}{m:02d}.pkl"
    out = AGG/f"min_{y}{m:02d}.csv"
    if out.exists():
        print(f"{y}-{m:02d} cached"); return
    s = datetime.datetime(y, m, 1)
    e = datetime.datetime(y+(m // 12), m % 12+1, 1)
    assert e <= datetime.datetime(2024, 1, 1), "FIREWALL: never fetch 2024+"
    df = None
    for attempt in range(8):
        try:
            df = fetch('xau/usd', INTERVAL_TICK, OFFER_SIDE_BID, s, e)
            if df is None or len(df) == 0:
                raise ValueError("empty response (rate limit?)")
            df = df.reset_index()
            for c in ["bidPrice", "askPrice"]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            if df[["bidPrice", "askPrice"]].isna().all().all():
                raise ValueError("non-numeric prices")
            break
        except Exception as ex:
            print(f"retry {y}-{m:02d} attempt {attempt}: {str(ex)[:100]}", flush=True)
            time.sleep(90)
    else:
        print(f"GAP {y}-{m:02d} FAILED after retries"); return
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df.to_pickle(key)
    df["mid"] = (df.bidPrice+df.askPrice)/2
    df["spread"] = df.askPrice-df.bidPrice
    g = df.set_index("timestamp")
    agg = pd.DataFrame({
        "mid_close": g.mid.resample("min").last(),
        "spread_mean": g.spread.resample("min").mean(),
        "spread_max": g.spread.resample("min").max(),
        "n_ticks": g.spread.resample("min").count(),
    }).dropna(subset=["mid_close"])
    agg.reset_index().to_csv(out, index=False)
    print(f"{y}-{m:02d} ticks={len(df)} minutes={len(agg)}", flush=True)

if __name__ == "__main__":
    y, m = int(sys.argv[1]), int(sys.argv[2])
    one_month(y, m)
