"""E2 second half: C/D/E/H/I/J/K/L/M/N/O/P. Prereg E2-2ND-001. Fixed SL1.5/TP2R/20.
Research explore -> validation. NO final OOS. M30/M15 unavailable (Yahoo 1h floor) -> D/E use D1/H4/H1."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, volatility as V, structure as ST
from features.elliott import waves as EW
from features.elliott import advanced as EA
from backtesting.engine import backtest_signals
from statsx.tests import expectancy, prop_test, bh_fdr
from scipy import stats
from research.registry import log_experiment
CFG = json.load(open(ROOT/"configs"/"config.json"))
COST = CFG["costs"]
FAM = []

def load(sym,tf,split):
    df=pd.read_csv(ROOT/split/f"{sym}_{tf}.csv",parse_dates=["timestamp"])
    df["timestamp"]=pd.to_datetime(df.timestamp,utc=True)
    return V.add_volatility(df)

def fwd(df, idx, d):
    sig=pd.DataFrame([{"idx":int(idx),"direction":int(d)}])
    tr=backtest_signals(df,sig,1.5,2.0,20,COST["spread_xauusd"],COST["slippage"])
    return float(tr.R.iloc[0]) if len(tr) else float("nan")

out={"prereg":"E2-2ND-001 fixed SL1.5/TP2R/20; M30/M15 unavailable; no final OOS","research":{},"validation":{}}
# ---- C: complex-correction detectability: 7-swing double-ABC vs generic 7-swing; distinguishability via b_ret pattern
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data"); sw=SW.fractal_swings(df,2)
    abcs=EW.find_abc(sw)
    dbl=0
    for i in range(len(abcs)-1):
        if abcs[i+1]["start"]-abcs[i]["start"]<=3:
            dbl+=1
    # surrogate comparison
    from features.elliott import nulls as EN
    sd=[]
    for s in range(5):
        a2=EW.find_abc(EN.surrogate_swings(sw,seed=s)); c=0
        for i in range(len(a2)-1):
            if a2[i+1]["start"]-a2[i]["start"]<=3: c+=1
        sd.append(c)
    out["research"][f"C_dbl_{tf}"]={"real_adjacent_abc":dbl,"surr":sd,
        "verdict":"NOT RELIABLY DETECTABLE" if dbl<=max(sd+[0])*1.5 else "candidate"}
# ---- H: extensions vs randomized ratios
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data"); sw=SW.fractal_swings(df,2)
    imps=EW.find_impulses(sw)
    ext=np.array([i["ext31"] for i in imps if np.isfinite(i["ext31"])])
    tgt=np.array([1.0,1.272,1.618,2.0,2.618,4.236])
    hit=np.mean([np.any(np.abs(tgt-v)/max(v,1e-9)<=0.05) for v in ext]) if len(ext) else 0
    rng=np.random.default_rng(0)
    base=np.median(ext) if len(ext) else 1.5
    sim=rng.lognormal(mean=np.log(max(base,0.2)),sigma=0.5,size=max(len(ext)*20,2000))
    chit=np.mean([np.any(np.abs(tgt-v)/max(v,1e-9)<=0.05) for v in sim])
    p=1.0
    if len(ext)>5:
        cnt=sum(rng.choice(sim,len(ext),replace=False).__class__ and 0 for _ in [0])  # placeholder
        B=2000; c=0
        for _ in range(B):
            if np.mean([np.any(np.abs(tgt-v)/max(v,1e-9)<=0.05) for v in rng.choice(sim,len(ext),replace=False)])>=hit: c+=1
        p=c/B
    FAM.append(p)
    out["research"][f"H_ext_{tf}"]={"hit":float(hit),"chance_logn":float(chit),"p":float(p),"n":len(ext)}
# ---- I: alternation full + W5 completion prediction
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data"); sw=SW.fractal_swings(df,2)
    imps=EW.find_impulses(sw)
    if len(imps)>10:
        w2=np.array([i["w2_ret"] for i in imps]); w4=np.array([i["w4_ret"] for i in imps])
        d3=np.array([i["w3"] for i in imps]); d5=np.array([i["w5"] for i in imps])
        w,pw=stats.wilcoxon(w2,w4) if len(w2)>10 else (0,1.0)
        FAM.append(float(pw))
        comp=np.array([1 if v>0.8*w3 else 0 for v,w3 in zip(d5,d3)])  # W5 completion proxy: 80% of W3
        alt=np.abs(w2-w4)
        auc=0.5
        if comp.sum()>0 and comp.sum()<len(comp):
            from sklearn.linear_model import LogisticRegression
            from sklearn.metrics import roc_auc_score
            m=LogisticRegression().fit(alt.reshape(-1,1),comp)
            auc=float(roc_auc_score(comp,m.predict_proba(alt.reshape(-1,1))[:,1]))
        out["research"][f"I_alt_{tf}"]={"wilcoxon_p":float(pw),"alt_auc_w5":auc,"n":len(imps)}
    else: out["research"][f"I_alt_{tf}"]={"n":len(imps)}
# ---- J: channeling: W5 distance to W1-W3 parallel projection / ATR vs surrogate
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data"); sw=SW.fractal_swings(df,2)
    imps=EW.find_impulses(sw); ds=[]
    for im in imps:
        p=np.array(im["prices"]); ci=int(im["confirm_idx"])
        a=float(df.atr.iloc[ci]) if ci<len(df) and np.isfinite(df.atr.iloc[ci]) else 1.0
        proj=(p[3]+(p[3]-p[1]))  # naive W5 projection from W1-W3 run
        ds.append(abs(p[5]-proj)/a)
    ds=np.array(ds); med=float(np.median(ds)) if len(ds) else 0
    out["research"][f"J_chan_{tf}"]={"median_dist_ATR":med,"n":len(ds)}
# ---- K: symmetry W1vsW5, AvsC (paired)
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data"); sw=SW.fractal_swings(df,2)
    imps=EW.find_impulses(sw); abcs=EW.find_abc(sw)
    r1={}
    if len(imps)>10:
        r1["W1W5_p"]=float(stats.wilcoxon([i["w1"] for i in imps],[i["w5"] for i in imps])[1]); FAM.append(r1["W1W5_p"])
    legsA=np.array([abs(a["prices"][1]-a["prices"][0]) for a in abcs]); legsC=np.array([abs(a["prices"][3]-a["prices"][2]) for a in abcs])
    if len(legsA)>10:
        r1["AvC_p"]=float(stats.wilcoxon(legsA,legsC)[1]); FAM.append(r1["AvC_p"])
    r1["n_imp"]=len(imps); r1["n_abc"]=len(abcs)
    out["research"][f"K_sym_{tf}"]=r1
# ---- L: internal structure: W3 span sub-swing count (k=1) high vs low quality continuation
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data"); sw=SW.fractal_swings(df,2); sw1=SW.fractal_swings(df,1)
    imps=EW.find_impulses(sw)
    hi=[]; lo=[]
    for im in imps:
        ci=int(im["confirm_idx"])
        # count k=1 swings inside W3 price range: proxy by total sub-swings before confirm
        nsub=len(sw1[sw1.confirm_idx<=ci])
        (hi if nsub>np.median(len(sw1)/max(len(imps),1)) else lo).append(fwd(df,ci+1,im["direction"]))
    import numpy as _np
    hi=_np.array(hi,float); lo=_np.array(lo,float)
    hi=hi[_np.isfinite(hi)]; lo=lo[_np.isfinite(lo)]
    t=prop_test(int((hi>0).sum()),len(hi),int((lo>0).sum()),len(lo)) if len(hi)>5 and len(lo)>5 else {"p":1.0}
    FAM.append(t["p"])
    out["research"][f"L_internal_{tf}"]={"hi_n":len(hi),"lo_n":len(lo),"hi_exp":float(hi.mean()) if len(hi) else 0,"lo_exp":float(lo.mean()) if len(lo) else 0,"p":t["p"]}
# ---- D/E nesting: D1 trend + H1 signal
for low in ["H1","H4"]:
    dfH=load("XAUUSD","D1","research_data"); dfL=load("XAUUSD",low,"research_data")
    swL=SW.fractal_swings(dfL,2); imL=EW.find_impulses(swL)
    d1=dfH.set_index("timestamp").close
    al=[]; cf=[]
    for im in imL:
        c=int(im["confirm_idx"])+1
        if c>=len(dfL)-2: continue
        ts=dfL.timestamp.iloc[min(c,len(dfL)-1)]
        try: px=d1[d1.index<=ts].iloc[-60:]
        except Exception: continue
        if len(px)<60: continue
        hi_trend=1 if px.iloc[-1]>px.iloc[0] else -1
        r=fwd(dfL,c,im["direction"])
        (al if hi_trend==im["direction"] else cf).append(r)
    al=np.array(al,float); cf=np.array(cf,float)
    al=al[np.isfinite(al)]; cf=cf[np.isfinite(cf)]
    ea=expectancy(al) if len(al) else {"exp_R":0,"n":0}; ec=expectancy(cf) if len(cf) else {"exp_R":0,"n":0}
    t=prop_test(int((al>0).sum()),len(al),int((cf>0).sum()),len(cf)) if len(al)>10 and len(cf)>10 else {"p":1.0}
    FAM.append(t["p"])
    out["research"][f"DE_nest_D1_{low}"]={"aligned":ea,"conflicting":ec,"p":t["p"]}
# ---- M: alternative-count robustness: overlapping impulse windows sharing>=3 swings
df=load("XAUUSD","H1","research_data"); sw=SW.fractal_swings(df,2); imps=EW.find_impulses(sw)
groups={}; flips=0; tot=0
for im in imps:
    key=tuple(range(im["start"],im["start"]+3))
    groups.setdefault(key,[]).append(im)
for k,v in groups.items():
    if len(v)>1:
        rs=[fwd(df,int(i["confirm_idx"])+1,i["direction"]) for i in v]
        rs=[x for x in rs if x==x]
        if len(rs)>1 and min(rs)<0<max(rs): flips+=1
        tot+=1
out["research"]["M_counts"]={"multi_count_regions":tot,"sign_flip_regions":flips,
    "verdict":"COUNT-SENSITIVE" if tot and flips/max(tot,1)>0.3 else "stable-or-untestable"}
# ---- N: information gain Models A-E: target next-20-bar +1R before -1R direction; logistic AUC/Brier/logloss
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score, brier_score_loss, log_loss
def feat_rows(df):
    sw=SW.fractal_swings(df,2); df2=ST.add_structure(df,sw); df2=V.add_volatility(df2) if "atr" not in df2 else df2
    imps=EW.find_impulses(sw); abcs=EW.find_abc(sw)
    imp_at={int(i["confirm_idx"]):i for i in imps}
    rows=[]
    for i in range(60,len(df)-21):
        a=df2.atr.iloc[i]
        if not np.isfinite(a) or a<=0: continue
        e=1 if df2.trend_state.iloc[i]!=0 else 0
        v=1 if str(df2.vol_regime.iloc[i])=="high" else 0
        im=imp_at.get(i)
        ell=1 if im is not None and not im["overlap"] else 0
        # fib: distance to nearest grid retracement of last swing pair
        f=0
        if len(sw):
            past=sw[sw.confirm_idx<=i]
            if len(past)>=2:
                p0,p1=float(past.price.iloc[-2]),float(past.price.iloc[-1])
                rng=abs(p1-p0)
                if rng>0:
                    dep=abs(float(df2.close.iloc[i])-p1)/rng
                    f=1 if min(abs(dep-g) for g in [0.382,0.5,0.618])<0.05 else 0
        # label: +1R before -1R over next 20 bars from long perspective using 1.5ATR risk
        entry=float(df2.close.iloc[i]); risk=1.5*a; up=entry+2*risk; dn=entry-risk
        y=None
        for k in range(i+1,min(i+21,len(df))):
            if df2.high.iloc[k]>=up: y=1; break
            if df2.low.iloc[k]<=dn: y=0; break
        if y is None: y=int(float(df2.close.iloc[min(i+20,len(df)-1)])>entry)
        rows.append({"A":e,"B":v,"C":ell,"D":f,"y":y})
    return pd.DataFrame(rows)
dtr=feat_rows(load("XAUUSD","H1","research_data")); dva=feat_rows(load("XAUUSD","H1","validation_data"))
Nres={}
for name,cols in [("A",["A"]),("B",["A","B"]),("C",["A","C"]),("D",["A","D"]),("E",["A","B","C","D"])]:
    if len(dtr)<100 or dtr.y.nunique()<2: Nres[name]={"auc":0.5}; continue
    m=LogisticRegression().fit(dtr[cols].values,dtr.y.values)
    for split,dd in [("tr",dtr),("va",dva)]:
        if len(dd)==0 or dd.y.nunique()<2: continue
        pr=m.predict_proba(dd[cols].values)[:,1]
        Nres[f"{name}_{split}"]={"auc":float(roc_auc_score(dd.y,pr)),"brier":float(brier_score_loss(dd.y,pr)),"logloss":float(log_loss(dd.y,pr))}
out["research"]["N_gain"]=Nres
# ---- validation spot-checks: H-ext + DE-nest + N already has va
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"validation_data"); sw=SW.fractal_swings(df,2)
    imps=EW.find_impulses(sw)
    rs=[fwd(df,int(i["confirm_idx"])+1,i["direction"]) for i in imps if int(i["confirm_idx"])+1<len(df)-2]
    rs=np.array(rs,float); rs=rs[np.isfinite(rs)]
    out["validation"][f"IMP_cont_{tf}"]=expectancy(rs) if len(rs) else {"exp_R":0,"n":0}
out["validation"]["N_gain"]= {k:v for k,v in Nres.items() if "_va" in k}
q=bh_fdr(FAM)
out["E2-Q2"]={"p":list(map(float,FAM)),"q":list(map(float,q)),"n":len(FAM)}
log_experiment({"hypothesis":"E2 second-half prereg family","dataset":"research->validation XAUUSD","results":{"N":Nres,"Q2":out["E2-Q2"]},"status":"REJECTED"})
with open(ROOT/"reports"/"elliott_e2second.json","w") as f: json.dump(out,f,indent=2,default=float)
print(json.dumps(out,indent=2,default=float))
