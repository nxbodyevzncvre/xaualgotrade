"""E2 first batch: A diagonals, B triangles, F partial, G invalidation.
Fixed execution SL1.5/TP2R/20. Research explore -> validation. NO final OOS. E1 untouched."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, volatility as V, structure as ST
from features.elliott import advanced as EA
from backtesting.engine import backtest_signals
from statsx.tests import expectancy, trade_stats, prop_test, bh_fdr
from research.registry import log_experiment
CFG = json.load(open(ROOT/"configs"/"config.json"))
COST = CFG["costs"]
EID = "E2-ABFG-001"

def load(sym,tf,split):
    df=pd.read_csv(ROOT/split/f"{sym}_{tf}.csv",parse_dates=["timestamp"])
    df["timestamp"]=pd.to_datetime(df.timestamp,utc=True)
    return V.add_volatility(df)

def fwd(df, idx, d):
    sig=pd.DataFrame([{"idx":int(idx),"direction":int(d)}])
    tr=backtest_signals(df,sig,1.5,2.0,20,COST["spread_xauusd"],COST["slippage"])
    return float(tr.R.iloc[0]) if len(tr) else float("nan")

def simple_trend_signals(df):
    df2=ST.add_structure(df, SW.fractal_swings(df,2))
    return pd.DataFrame([{"idx":i,"direction":int(s)} for i,s in enumerate(df2.trend_state) if s!=0 and i<len(df)-21])

def breakout_signals(df):
    c=df.close; hh=c.rolling(20).max().shift(1); ll=c.rolling(20).min().shift(1)
    r=[]
    for i in range(20,len(df)-21):
        if c.iloc[i]>hh.iloc[i]: r.append({"idx":i+1,"direction":1})
        elif c.iloc[i]<ll.iloc[i]: r.append({"idx":i+1,"direction":-1})
    return pd.DataFrame(r)

out={"prereg":"E2-ABFG-001 fixed SL1.5/TP2R/20; family=FDR; E1 untouched; no final OOS","research":{},"validation":{}}
pvals=[]
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data")
    sw=SW.fractal_swings(df,2)
    # A: diagonals vs generic converging
    dg=EA.diagonal_candidates(sw,df.atr); gc=EA.generic_converging(sw,df.atr)
    rd=[fwd(df,int(d["confirm_idx"])+1,-d["direction"]) for d in dg if int(d["confirm_idx"])+1<len(df)-2]  # reversal hypothesis for ending-like
    rc=[fwd(df,int(g["confirm_idx"])+1,1 if g["direction"]>=0 else -1) for g in gc if int(g["confirm_idx"])+1<len(df)-2]
    rd=np.array(rd,float); rc=np.array(rc,float)
    rd=rd[np.isfinite(rd)]; rc=rc[np.isfinite(rc)]
    er=expectancy(rd) if len(rd) else {"exp_R":0,"n":0}
    ec=expectancy(rc) if len(rc) else {"exp_R":0,"n":0}
    t=prop_test(int((rd>0).sum()),len(rd),int((rc>0).sum()),len(rc)) if len(rd)>5 and len(rc)>5 else {"p":1.0}
    pvals.append(t["p"])
    out["research"][f"A_diag_{tf}"]={"n_diag":len(dg),"n_conv":len(gc),"diag_rev":er,"conv_cont":ec,"winrate_test_p":t["p"]}
    # B: triangles pre-breakout; outcome = breakout within 20 bars
    trs=EA.triangle_candidates(sw,df.atr)
    bykinds={}
    for tkind in ["contracting","barrier","expanding","running_suspect"]:
        sub=[t for t in trs if t["kind"]==tkind]
        wins=0; tested=0; mags=[]
        for t2 in sub:
            c=int(t2["confirm_idx"])
            if c+21>=len(df): continue
            post=df.iloc[c+1:c+21]
            up=(post.close> t2["hi"]).any(); dn=(post.close < t2["lo"]).any()
            if up or dn:
                tested+=1
                first_up=(post.close> t2["hi"]).idxmax() if up else None
                first_dn=(post.close< t2["lo"]).idxmax() if dn else None
                # continuation proxy: close-to-close 20-bar drift direction matches first break
                drift=float(df.close.iloc[min(c+20,len(df)-1)]-df.close.iloc[c+1])
                brk=1 if (up and (not dn or first_up<=first_dn)) else -1
                wins+=int((drift>0)==(brk>0))
                mags.append(abs(drift)/ (df.atr.iloc[c] if np.isfinite(df.atr.iloc[c]) else 1))
        bykinds[tkind]={"n":len(sub),"tested":tested,"dir_accuracy":wins/tested if tested else 0,
            "median_mag_ATR":float(np.median(mags)) if mags else 0}
    out["research"][f"B_tri_{tf}"]=bykinds
    # F: partial prefixes -> completion + forward R
    prefs=EA.partial_prefixes(sw)
    comp={}
    for k in ["1-2","A-B","1-2-3start","tri-A-B-C-D"]:
        sub=[p for p in prefs if p["kind"]==k]
        rs=[fwd(df,int(p["confirm_idx"])+1,1)+0 for p in sub if int(p["confirm_idx"])+1<len(df)-2]
        # direction unknown at partial stage -> use absolute move proxy: use sign of last leg
        rs2=[]
        for p in sub:
            c=int(p["confirm_idx"])+1
            if c+20>=len(df): continue
            drift=float(df.close.iloc[c+5]-df.close.iloc[c])
            rs2.append(abs(drift)/(df.atr.iloc[c] if np.isfinite(df.atr.iloc[c]) else 1))
        comp[k]={"n":len(sub),"median_abs5b_ATR":float(np.median(rs2)) if rs2 else 0}
    out["research"][f"F_partial_{tf}"]=comp
    # G: invalidation vs generic failure -> next-5-bar reversal?
    evs=EA.invalidation_events(sw,df); gev=EA.generic_swing_failure(sw,df)
    def rev_rate(evs):
        r=0;n=0
        for e in evs:
            k=int(e["event_idx"])
            if k+5>=len(df): continue
            a=df.atr.iloc[k]
            if not np.isfinite(a) or a<=0: continue
            # reversal = price moves opposite prior direction by 0.5 ATR in 5 bars
            mv=float(df.close.iloc[k+5]-df.close.iloc[k]) * (-e["direction"])
            n+=1; r+=int(mv>0.5*a)
        return r/n if n else 0, n
    re,ne=rev_rate(evs); rg,ng=rev_rate(gev)
    t2=prop_test(int(re*ne),ne,int(rg*ng),ng) if ne>10 and ng>10 else {"p":1.0}
    pvals.append(t2["p"])
    out["research"][f"G_inv_{tf}"]={"elliott_rev":re,"elliott_n":ne,"generic_rev":rg,"generic_n":ng,"p":t2["p"]}

# validation: repeat A-reversal + G-reversal only (pre-registered)
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"validation_data")
    sw=SW.fractal_swings(df,2)
    dg=EA.diagonal_candidates(sw,df.atr)
    rd=[fwd(df,int(d["confirm_idx"])+1,-d["direction"]) for d in dg if int(d["confirm_idx"])+1<len(df)-2]
    rd=np.array(rd,float); rd=rd[np.isfinite(rd)]
    out["validation"][f"A_diag_{tf}"]=expectancy(rd) if len(rd) else {"exp_R":0,"n":0}
    evs=EA.invalidation_events(sw,df)
    r=0;n=0
    for e in evs:
        k=int(e["event_idx"])
        if k+5>=len(df): continue
        a=df.atr.iloc[k]
        if not np.isfinite(a) or a<=0: continue
        mv=float(df.close.iloc[k+5]-df.close.iloc[k])*(-e["direction"])
        n+=1; r+=int(mv>0.5*a)
    out["validation"][f"G_inv_{tf}"]={"rev_rate":r/n if n else 0,"n":n}
    # baselines E2-P on validation H1/D1
    for name,fn in [("trend",simple_trend_signals),("breakout",breakout_signals)]:
        sig=fn(df)
        tr=backtest_signals(df,sig,1.5,2.0,20,COST["spread_xauusd"],COST["slippage"]) if len(sig) else pd.DataFrame()
        e=expectancy(tr.R.values) if len(tr) else {"exp_R":0,"n":0}
        out["validation"][f"P_base_{name}_{tf}"]={"exp_R":e.get("exp_R",0),"n":e.get("n",0)}

q=bh_fdr(pvals)
out["E2-Q_multiple_testing"]={"family_p":pvals,"q_fdr":list(map(float,q)),"n_tests":len(pvals)}
log_experiment({"hypothesis":"E2-ABFG preregistered family","dataset":"research->validation XAUUSD","results":out,"status":"VALIDATED" if any(v.get("exp_R",0)>0 and v.get("ci_lo",-1)>0 for v in out["validation"].values() if isinstance(v,dict)) else "REJECTED"})
with open(ROOT/"reports"/"elliott_e2abfg.json","w") as f: json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
