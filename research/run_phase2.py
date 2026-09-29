"""Phase 2 (preregistered, exploratory): silver transfer + missing baselines + cycle screen + extensions + sessions.
Does NOT alter frozen XAUUSD verdict; does NOT re-run XAUUSD final test."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, fibonacci as FIB, volatility as V, structure as ST
from backtesting.engine import backtest_signals
from statsx.tests import prop_test, expectancy, trade_stats
from statsmodels.stats.diagnostic import acorr_breusch_godfrey
from research.registry import log_experiment
CFG = json.load(open(ROOT/"configs"/"config.json"))
COST = CFG["costs"]
out = {}

def load(sym, tf, split):
    df = pd.read_csv(ROOT/split/f"{sym}_{tf}.csv", parse_dates=["timestamp"])
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    return V.add_volatility(df)

# 1. Silver transfer: identical EXP-01 + candidate rule
for tf in ["D1", "H1"]:
    df = load("XAGUSD", tf, "research_data")
    sw = SW.fractal_swings(df, 2); df = ST.add_structure(df, sw)
    pairs = FIB.pairs_to_retracements(sw)
    react = FIB.measure_reactions(df, pairs, CFG["fib_levels"])
    fib = react[react.kind=="fib"]; rnd = react[react.kind=="random"]
    ft = fib[fib.touched]; rt = rnd[rnd.touched]
    t = prop_test(int(ft.reacted.sum()), len(ft), int(rt.reacted.sum()), len(rt))
    out[f"SILVER_EXP01_{tf}"] = {"fib_rate": float(ft.reacted.mean()) if len(ft) else 0, "rand_rate": float(rt.reacted.mean()) if len(rt) else 0, "test": t}
    log_experiment({"hypothesis": "H8 transfer: silver fib reaction", "dataset": f"research XAGUSD {tf}", "results": out[f"SILVER_EXP01_{tf}"], "status": "PROMISING" if t["p"]<0.05 else "REJECTED"})
    # transfer frozen candidate (50% high-vol fade)
    sigs = []
    for _, r in pairs.iterrows():
        c0=int(r.confirm_idx)
        if c0+1>=len(df): continue
        if df.vol_regime.iloc[c0]!="high": continue
        lp=FIB.level_price(r.lo,r.hi,0.5,r.direction)
        d=1 if df.close.iloc[c0]<lp else -1
        sigs.append({"idx":c0+1,"direction":-d})
    tr=backtest_signals(df,pd.DataFrame(sigs),1.5,2.0,20,COST["spread_xauusd"],COST["slippage"])
    e=expectancy(tr.R.values) if len(tr) else {"exp_R":0,"n":0}
    out[f"SILVER_CAND_{tf}_research"]=e
    dfv=load("XAGUSD",tf,"validation_data")
    swv=SW.fractal_swings(dfv,2); dfv=ST.add_structure(dfv,swv); pv=FIB.pairs_to_retracements(swv)
    sigs=[]
    for _,r in pv.iterrows():
        c0=int(r.confirm_idx)
        if c0+1>=len(dfv): continue
        if dfv.vol_regime.iloc[c0]!="high": continue
        lp=FIB.level_price(r.lo,r.hi,0.5,r.direction)
        d=1 if dfv.close.iloc[c0]<lp else -1
        sigs.append({"idx":c0+1,"direction":-d})
    trv=backtest_signals(dfv,pd.DataFrame(sigs),1.5,2.0,20,COST["spread_xauusd"],COST["slippage"])
    out[f"SILVER_CAND_{tf}_validation"]=expectancy(trv.R.values) if len(trv) else {"exp_R":0,"n":0}
    log_experiment({"hypothesis":"H8 transfer candidate validation","dataset":f"XAGUSD {tf}","results":out[f"SILVER_CAND_{tf}_validation"],"status":"VALIDATED" if out[f"SILVER_CAND_{tf}_validation"].get("exp_R",0)>0 and out[f"SILVER_CAND_{tf}_validation"].get("ci_lo",-1)>0 else "REJECTED"})

# 2. Missing baselines on XAUUSD validation H1
dfv = load("XAUUSD","H1","validation_data")
close=dfv.close
# SMA 20/50 cross
sma20=close.rolling(20).mean(); sma50=close.rolling(50).mean()
sig=pd.DataFrame([{"idx":i,"direction":1 if sma20.iloc[i]>sma50.iloc[i] else -1} for i in range(50,len(dfv)-21)])
tr=backtest_signals(dfv,sig,1.5,2.0,20,COST["spread_xauusd"],COST["slippage"])
out["BASE_SMA_H1_val"]=expectancy(tr.R.values) if len(tr) else {"exp_R":0,"n":0}
# ATR breakout: close > prior 20h high
hh=close.rolling(20).max().shift(1); ll=close.rolling(20).min().shift(1)
rows=[]
for i in range(20,len(dfv)-21):
    if close.iloc[i]>hh.iloc[i]: rows.append({"idx":i+1,"direction":1})
    elif close.iloc[i]<ll.iloc[i]: rows.append({"idx":i+1,"direction":-1})
tr=backtest_signals(dfv,pd.DataFrame(rows),1.5,2.0,20,COST["spread_xauusd"],COST["slippage"])
out["BASE_ATRBREAK_H1_val"]=expectancy(tr.R.values) if len(tr) else {"exp_R":0,"n":0}
# buy-hold R approx
a=dfv.atr.dropna().mean()
bh=(dfv.close.iloc[-1]-dfv.close.iloc[0])/ (1.5*a) if a==a and a>0 else 0
out["BASE_BUYHOLD_H1_val"]={"R_total":float(bh)}

# 3. Cycle screen: autocorr of H1/D1 research returns + Hurst
from statsmodels.tsa.stattools import acf
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data")
    r=df.close.pct_change().dropna().values
    a=acf(r, nlags=20, fft=False)
    from features.volatility import hurst
    out[f"CYCLE_{tf}"]= {"acf_lag1_5": [float(x) for x in a[1:6]], "max_abs_acf_1_20": float(np.abs(a[1:]).max()), "hurst_full": float(hurst(r))}
    log_experiment({"hypothesis":"cycles persist OOS","dataset":f"research XAUUSD {tf}","results":out[f"CYCLE_{tf}"],"status":"PROMISING" if out[f"CYCLE_{tf}"]["max_abs_acf_1_20"]>0.08 else "REJECTED"})

# 4. Extensions 1.272/1.618 touch-rate vs random offset (research H1)
df=load("XAUUSD","H1","research_data")
sw=SW.fractal_swings(df,2); pairs=FIB.pairs_to_retracements(sw)
rng=np.random.default_rng(11); hits={1.272:[0,0],1.618:[0,0]}
for _,p in pairs.iterrows():
    c0=int(p.confirm_idx)
    if c0+30>=len(df): continue
    a=df.atr.iloc[c0]
    if not np.isfinite(a) or a<=0: continue
    rng_ext=float(rng.uniform(1.05,1.8))
    for ext in [1.272,1.618]:
        tgt=p.hi+(p.hi-p.lo)*(ext-1) if p.direction=="up" else p.lo-(p.hi-p.lo)*(ext-1)
        seg=df.high.iloc[c0+1:c0+21].max() if p.direction=="up" else df.low.iloc[c0+1:c0+21].min()
        hit=(seg>=tgt-0.25*a) if p.direction=="up" else (seg<=tgt+0.25*a)
        hits[ext][1]+=1; hits[ext][0]+=int(bool(hit))
out["EXT_H1"]={str(k):{"hit_rate":v[0]/v[1] if v[1] else 0,"n":v[1]} for k,v in hits.items()}

# 5. Session split of frozen-candidate trades (research H1)
df=load("XAUUSD","H1","research_data")
sw=SW.fractal_swings(df,2); df=ST.add_structure(df,sw); pairs=FIB.pairs_to_retracements(sw)
sigs=[]
for _,r in pairs.iterrows():
    c0=int(r.confirm_idx)
    if c0+1>=len(df): continue
    if df.vol_regime.iloc[c0]!="high": continue
    lp=FIB.level_price(r.lo,r.hi,0.5,r.direction)
    d=1 if df.close.iloc[c0]<lp else -1
    sigs.append({"idx":c0+1,"direction":-d})
tr=backtest_signals(df,pd.DataFrame(sigs),1.5,2.0,20,COST["spread_xauusd"],COST["slippage"])
if len(tr):
    hrs=pd.to_datetime(df.timestamp).dt.hour
    for sess,name in [(range(0,8),"asian"),(range(7,12),"london"),(range(12,17),"newyork")]:
        idx=[i for i in tr.entry_idx if int(hrs.iloc[min(int(i),len(hrs)-1)]) in sess]
        sub=tr[tr.entry_idx.isin(idx)]
        out[f"SESSION_{name}"] = expectancy(sub.R.values) if len(sub) else {"exp_R":0,"n":0}

with open(ROOT/"reports"/"phase2_report.json","w") as f: json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
