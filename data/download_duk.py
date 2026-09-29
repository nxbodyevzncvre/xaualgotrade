"""Primary data: Dukascopy spot XAUUSD H1 (+D1 resample). Yahoo GC=F kept as secondary."""
import sys
from pathlib import Path
import pandas as pd, datetime
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.adapter import save_raw
from data.quality import quality_report
from dukascopy_python import fetch, INTERVAL_HOUR_1, OFFER_SIDE_BID

frames = []
for y in range(2020, 2027):
    s, e = datetime.datetime(y, 1, 1), datetime.datetime(y+1, 1, 1)
    print(f"fetch {y} ...", flush=True)
    df = fetch('xau/usd', INTERVAL_HOUR_1, OFFER_SIDE_BID, s, e)
    df = df.reset_index().rename(columns={"open": "open", "high": "high", "low": "low", "close": "close", "volume": "tick_volume"})
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    frames.append(df[["timestamp", "open", "high", "low", "close", "tick_volume"]])
h1 = pd.concat(frames).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
p = save_raw(h1, "XAUUSD", "H1", "dukascopy", {"instrument": "xau/usd", "offer": "bid"})
print("saved", p, len(h1), h1.timestamp.iloc[0], "->", h1.timestamp.iloc[-1])
print(quality_report(h1))
d1 = h1.set_index("timestamp").resample("1D").agg({"open": "first", "high": "max", "low": "min", "close": "last", "tick_volume": "sum"}).dropna().reset_index()
p2 = save_raw(d1, "XAUUSD", "D1", "dukascopy", {"resampled_from": "H1"})
print("saved", p2, len(d1))
# date-based splits for primary
r = h1[h1.timestamp < "2023-01-01"]; v = h1[(h1.timestamp >= "2023-01-01") & (h1.timestamp < "2024-01-01")]; f = h1[h1.timestamp >= "2024-01-01"]
for name, d in [("research_data", r), ("validation_data", v), ("final_test_data", f)]:
    d.to_csv(ROOT/name/"XAUUSD_H1_duk.csv", index=False)
print("PRIMARY SPLIT H1:", len(r), len(v), len(f))
