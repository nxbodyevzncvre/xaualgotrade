"""R5 R-target rerun with corrected entry mapping.
BUG DOCUMENTED: prior run mapped M5 label :00 -> M1 :00 bar (stale entry inside signal window).
M5 resample uses left labels: bin :00 = M1 :00-:04, info complete at :05.
Correct entry: M1 :05 bar (first bar fully after decision; 1-min implementation lag, disclosed).
RAND control + ambiguity-as-loss retained."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import microstructure as MS
from features import volatility as V

m1v = pd.read_csv(ROOT/"validation_data"/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
m1v["timestamp"] = pd.to_datetime(m1v.timestamp, utc=True)
m1v = MS.session_filter(m1v)
m5v = MS.m5_frame(m1v); m5v = MS.f1_path(m1v, m5v)
ord60 = MS.f3_order(m1v, 60)
m1v["ord"] = ord60.values
last_ord = m1v.set_index("timestamp").groupby(pd.Grouper(freq="5min")).ord.last().reset_index()
m5v = m5v.merge(last_ord, left_on="timestamp", right_on="timestamp", how="left")
d = pd.Series(np.where(m5v.ret/m5v.atr14*m5v.close > 0.02, "UP",
              np.where(m5v.ret/m5v.atr14*m5v.close < -0.02, "DN", "NEU")), index=m5v.index)
m5v["d1"] = d
m1a = V.add_volatility(m1v)
H, L, Cc, Av = m1v.high.values, m1v.low.values, m1v.close.values, m1a.atr.values
tsidx = {t: i for i, t in enumerate(m1v.timestamp)}
dec = m5v.iloc[::6].reset_index(drop=True)
grp = {"F3_HF": ((dec.ord == "HF").values, 1), "F3_LF": ((dec.ord == "LF").values, -1),
       "F5_DN": ((dec.d1 == "DN").values, 1), "F5_UP": ((dec.d1 == "UP").values, -1)}
rng0 = np.random.default_rng(0)
rm = np.zeros(len(dec), bool); rm[rng0.choice(len(dec), size=len(dec)//4, replace=False)] = True
grp["RAND"] = (rm, None)
rdir = np.random.default_rng(1).choice([-1, 1], size=len(dec))
out = {}
for gk, (mk, dc) in grp.items():
    wins = n = 0; mfes = []; maes = []; und = 0
    for j in np.where(mk)[0]:
        ts = dec.timestamp.iloc[j]+pd.Timedelta(minutes=5)
        i = tsidx.get(ts, None)
        if i is None or i+60 >= len(Cc): und += 1; continue
        a = Av[i]
        if not np.isfinite(a) or a <= 0: continue
        dirc = rdir[j] if gk == "RAND" else dc
        entry, risk = Cc[i], 1.5*a
        up, dn = entry+dirc*risk, entry-dirc*risk
        res = None
        for k in range(i+1, min(i+61, len(Cc))):
            hu = (H[k] >= up) if dirc == 1 else (L[k] <= up)
            hd = (L[k] <= dn) if dirc == 1 else (H[k] >= dn)
            if hu and hd: res = 0; break
            if hu: res = 1; break
            if hd: res = 0; break
        if res is None: continue
        n += 1; wins += res
        if dirc == 1:
            mfes.append((H[i+1:i+61].max()-entry)/risk); maes.append((L[i+1:i+61].min()-entry)/risk)
        else:
            mfes.append((entry-L[i+1:i+61].min())/risk); maes.append((entry-H[i+1:i+61].max())/risk)
    out[gk] = {"n": n, "unmapped": int(und), "P_1R_before_1R": round(wins/n, 4) if n else None,
               "MFE_med": round(float(np.median(mfes)), 3) if mfes else None,
               "MAE_med": round(float(np.median(maes)), 3) if maes else None}
with open(ROOT/"reports"/"round5_R_fixed.json", "w") as f: json.dump(out, f, indent=2)
print(json.dumps(out, indent=2))
