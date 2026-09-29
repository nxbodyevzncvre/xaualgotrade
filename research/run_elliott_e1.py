"""Elliott E1 (order 23.34 steps 1-6 + info-gain + falsification). RESEARCH ONLY. Final locked."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, volatility as V
from features.elliott import waves as EW
from features.elliott import metrics as EM
from features.elliott import nulls as EN
from backtesting.engine import backtest_signals
from statsx.tests import expectancy, trade_stats, prop_test
from scipy import stats
from research.registry import log_experiment
CFG = json.load(open(ROOT/"configs"/"config.json"))
COST = CFG["costs"]
GRID = np.array([0.236,0.382,0.5,0.618,0.786])

def load(sym,tf,split):
    df=pd.read_csv(ROOT/split/f"{sym}_{tf}.csv",parse_dates=["timestamp"])
    df["timestamp"]=pd.to_datetime(df.timestamp,utc=True)
    return V.add_volatility(df)

def fwd_R(df, idx, direction, sl=1.5, tp=2.0, hold=20):
    sig=pd.DataFrame([{"idx":idx,"direction":direction}])
    tr=backtest_signals(df,sig,sl,tp,hold,COST["spread_xauusd"],COST["slippage"])
    return float(tr.R.iloc[0]) if len(tr) else float("nan")

def near_grid_rate(x, grid=GRID, tol=0.03):
    x=np.asarray(x,float); x=x[np.isfinite(x)]
    if len(x)==0: return 0.0,0
    hit=np.array([np.min(np.abs(g-x))<=tol for g in [x]])# placeholder
    h=np.mean([np.any(np.abs(grid-v)<=tol) for v in x])
    # chance under Uniform[0,1]: width covered
    cov=len(grid)*2*tol
    return float(h), float(min(cov,1.0))

out={}
for tf in ["D1","H1"]:
    df=load("XAUUSD",tf,"research_data")
    sw=SW.fractal_swings(df,CFG["swing"]["fractal_k"])
    imps=EW.find_impulses(sw); abcs=EW.find_abc(sw); tris=EW.find_contracting_triangle(sw)
    out[f"E_IMP_{tf}"]={"n_impulses":len(imps),"n_abc":len(abcs),"n_triangles":len(tris),
        "ext_w1":sum(1 for i in imps if (i["w1"]>= (i["w1"] or 1)) and i["ext31"]>2.5),
        "truncated":sum(1 for i in imps if i["truncated"]),"overlap":sum(1 for i in imps if i["overlap"])}
    # continuation: enter with impulse direction at completion+1
    Rs=[]
    for im in imps:
        c=int(im["confirm_idx"])+1
        if c < len(df)-2: Rs.append(fwd_R(df,c,im["direction"]))
    Rs=np.array(Rs,float); Rs=Rs[np.isfinite(Rs)]
    e=expectancy(Rs) if len(Rs) else {"exp_R":0,"n":0}
    ts=trade_stats(Rs) if len(Rs) else {}
    out[f"E_CONT_{tf}"]= {**e, **ts}
    # falsification: same detector on surrogate swings (5 seeds)
    surr=[]
    for s in range(5):
        sws=EN.surrogate_swings(sw,seed=s)
        im2=EW.find_impulses(sws)
        surr.append(len(im2))
    out[f"E_SURR_{tf}"]={"real":len(imps),"surr_counts":surr,"surr_mean":float(np.mean(surr)),
        "enrichment":float(len(imps)/max(np.mean(surr),1))}
    # ABC reversal: enter opposite of C leg? Convention: completion -> new motive in C direction
    Ra=[]
    for a in abcs:
        c=int(a["confirm_idx"])+1
        if c < len(df)-2: Ra.append(fwd_R(df,c,a["direction"]))
    Ra=np.array(Ra,float); Ra=Ra[np.isfinite(Ra)]
    out[f"E_ABC_{tf}"]= expectancy(Ra) if len(Ra) else {"exp_R":0,"n":0}
    # fib wave relationships
    w2=np.array([i["w2_ret"] for i in imps]); w4=np.array([i["w4_ret"] for i in imps])
    ext=np.array([i["ext31"] for i in imps]); ext=ext[np.isfinite(ext)]
    h2,c2=near_grid_rate(w2); h4,c4=near_grid_rate(w4)
    ks2=stats.kstest(w2[w2==w2],"uniform") if len(w2)>10 else (1.0,1.0)
    # extension concentration near 1.618/2.0/2.618 within 5%
    tgt=np.array([1.618,2.0,2.618]); he=np.mean([np.any(np.abs(tgt-v)/v<=0.05) for v in ext]) if len(ext) else 0
    # alternation: corr(W2,W4) should be negative under alternation; permutation p
    if len(w2)>10:
        r=np.corrcoef(w2,w4)[0,1]
        rng=np.random.default_rng(0); cnt=0; B=2000
        for _ in range(B):
            if abs(np.corrcoef(w2,rng.permutation(w4))[0,1])>=abs(r): cnt+=1
        p_alt=cnt/B
    else: r,p_alt=float("nan"),1.0
    out[f"E_FIB_{tf}"]={"w2_near_grid":h2,"chance":c2,"w4_near_grid":h4,"ks_w2_p":float(ks2[1]),
        "ext_hit_162_200_262":float(he),"alternation_corr":float(r),"alternation_p":float(p_alt),
        "n":len(imps)}
    for key in [f"E_CONT_{tf}",f"E_ABC_{tf}",f"E_FIB_{tf}"]:
        log_experiment({"hypothesis":"Elliott E1 "+key,"dataset":f"research XAUUSD {tf}",
            "results":out[key],"status":"PROMISING" if out[key].get("exp_R",0)>0 else "REJECTED"})
# motive-vs-corrective info gain: impulse-leg efficiency vs ABC-leg efficiency predicting continuation (H1)
df=load("XAUUSD","H1","research_data"); sw=SW.fractal_swings(df,2)
imps=EW.find_impulses(sw); abcs=EW.find_abc(sw)
rows=[]
for im in imps:
    c=int(im["confirm_idx"])+1
    if c<len(df)-2: rows.append({"eff":abs(im["w3"])/(abs(im["w1"])+abs(im["w3"])+abs(im["w5"])+1e-9),"overlap":int(im["overlap"]),"is_motive":1,"R":fwd_R(df,c,im["direction"])})
for a in abcs[:len(imps)]:
    c=int(a["confirm_idx"])+1
    if c<len(df)-2: rows.append({"eff":0.3,"overlap":1,"is_motive":0,"R":fwd_R(df,c,a["direction"])})
dd=pd.DataFrame(rows).dropna()
if len(dd)>50:
    from sklearn.linear_model import LogisticRegression
    from sklearn.metrics import roc_auc_score
    dd["y"]=(dd.R>0).astype(int)
    X=dd[["eff","overlap"]].values; y=dd.y.values
    m=LogisticRegression().fit(X,y)
    auc=float(roc_auc_score(y,m.predict_proba(X)[:,1]))
    out["E_CLASSIFIER_in_sample_AUC"]=auc
    # validation AUC
    dfv=load("XAUUSD","H1","validation_data"); swv=SW.fractal_swings(dfv,2)
    im2=EW.find_impulses(swv); ab2=EW.find_abc(swv); r2=[]
    for im in im2:
        c=int(im["confirm_idx"])+1
        if c<len(dfv)-2: r2.append({"eff":abs(im["w3"])/(abs(im["w1"])+abs(im["w3"])+abs(im["w5"])+1e-9),"overlap":int(im["overlap"]),"R":fwd_R(dfv,c,im["direction"])})
    for a in ab2[:len(im2)]:
        c=int(a["confirm_idx"])+1
        if c<len(dfv)-2: r2.append({"eff":0.3,"overlap":1,"R":fwd_R(dfv,c,a["direction"])})
    d2=pd.DataFrame(r2).dropna()
    if len(d2)>20:
        d2["y"]=(d2.R>0).astype(int)
        out["E_CLASSIFIER_val_AUC"]=float(roc_auc_score(d2.y,m.predict_proba(d2[["eff","overlap"]].values)[:,1])) if d2.y.nunique()>1 else 0.5
out["NOT_RELIABLE"]=EW.NOT_RELIABLE
with open(ROOT/"reports"/"elliott_e1.json","w") as f: json.dump(out,f,indent=2)
print(json.dumps(out,indent=2))
