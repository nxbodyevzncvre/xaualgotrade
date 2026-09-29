"""M5+M1 primary spot download, monthly chunks with resume. No resampling from H1."""
import sys, time
from pathlib import Path
import pandas as pd, datetime
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.adapter import save_raw
from data.quality import quality_report
from dukascopy_python import fetch, INTERVAL_MIN_5, INTERVAL_MIN_1, OFFER_SIDE_BID

CACHE = ROOT/"data"/"raw"/"_dukcache"; CACHE.mkdir(parents=True, exist_ok=True)

def months(a, b):
    cur = datetime.datetime(a.year, a.month, 1)
    end = datetime.datetime(b.year, b.month, 1)
    while cur <= end:
        nxt = datetime.datetime(cur.year+cur.month//12, cur.month % 12+1, 1)
        yield cur, min(nxt, b)
        cur = nxt

def dl(iv, tf, start, end):
    frames = []
    for s, e in months(start, end):
        key = CACHE/f"xau_{tf}_{s:%Y%m}.csv"
        if key.exists():
            frames.append(pd.read_csv(key, parse_dates=["timestamp"]))
            continue
        for attempt in range(3):
            try:
                df = fetch('xau/usd', iv, OFFER_SIDE_BID, s, e)
                break
            except Exception as ex:
                print(f"retry {s:%Y-%m} {ex}"[:120]); time.sleep(5)
        else:
            print(f"GAP {tf} {s:%Y-%m}"); continue
        df = df.reset_index().rename(columns={"volume": "tick_volume"})
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df[["timestamp","open","high","low","close","tick_volume"]]
        df.to_csv(key, index=False)
        frames.append(df)
        print(f"{tf} {s:%Y-%m} {len(df)}", flush=True)
    out = pd.concat(frames).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    return out

START, END = datetime.datetime(2020,1,1), datetime.datetime(2026,9,29)
for iv, tf in [(INTERVAL_MIN_5, "M5"), (INTERVAL_MIN_1, "M1")]:
    df = dl(iv, tf, START, END)
    p = save_raw(df, "XAUUSD", tf, "dukascopy", {"instrument": "xau/usd", "offer": "bid", "native": tf})
    print("saved", p, len(df), df.timestamp.iloc[0], "->", df.timestamp.iloc[-1])
    print(quality_report(df))
    r = df[df.timestamp < "2023-01-01"]; v = df[(df.timestamp >= "2023-01-01") & (df.timestamp < "2024-01-01")]; f = df[df.timestamp >= "2024-01-01"]
    for name, d in [("research_data", r), ("validation_data", v), ("final_test_data", f)]:
        d.to_csv(ROOT/name/f"XAUUSD_{tf}_duk.csv", index=False)
    print(f"SPLIT {tf}:", len(r), len(v), len(f))
