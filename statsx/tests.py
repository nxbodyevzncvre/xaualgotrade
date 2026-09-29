"""Statistical helpers: binomial, bootstrap, FDR, DSR approximation, metrics."""
import numpy as np
from scipy import stats

def prop_test(x1, n1, x2, n2):
    if n1 == 0 or n2 == 0:
        return {"diff": 0.0, "p": 1.0}
    p1, p2 = x1/n1, x2/n2
    p = (x1+x2)/(n1+n2)
    se = (p*(1-p)*(1/n1+1/n2)) ** 0.5
    if se == 0:
        return {"diff": p1-p2, "p": 1.0}
    z = (p1-p2)/se
    return {"diff": p1-p2, "p1": p1, "p2": p2, "z": z, "p": 2*(1-stats.norm.cdf(abs(z)))}

def bootstrap_ci(x, n_boot=2000, ci=0.95, seed=42):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, dtype=float)
    x = x[np.isfinite(x)]
    if len(x) == 0:
        return (float("nan"), float("nan"), float("nan"))
    m = x.mean()
    bs = [rng.choice(x, size=len(x), replace=True).mean() for _ in range(n_boot)]
    lo, hi = np.quantile(bs, [(1-ci)/2, 1-(1-ci)/2])
    return (float(m), float(lo), float(hi))

def bh_fdr(pvals):
    """Benjamini-Hochberg adjusted q-values."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    q = np.empty(n)
    prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        prev = min(prev, p[idx]*n/(n-rank+1))
        q[idx] = prev
    return q

def expectancy(R):
    R = np.asarray(R, dtype=float)
    R = R[np.isfinite(R)]
    if len(R) == 0:
        return {"exp_R": 0.0, "n": 0}
    m, lo, hi = bootstrap_ci(R)
    return {"exp_R": m, "ci_lo": lo, "ci_hi": hi, "n": len(R)}

def max_drawdown(equity):
    e = np.asarray(equity, dtype=float)
    peak = np.maximum.accumulate(e)
    dd = e - peak
    return float(dd.min()) if len(dd) else 0.0

def trade_stats(R):
    R = np.asarray(R, dtype=float)
    R = R[np.isfinite(R)]
    if len(R) == 0:
        return {"n": 0}
    wins = R[R > 0]
    losses = R[R <= 0]
    pf = wins.sum()/abs(losses.sum()) if len(losses) and losses.sum() != 0 else float("inf")
    return {"n": len(R), "win_rate": float((R > 0).mean()), "avg_win": float(wins.mean()) if len(wins) else 0.0,
            "avg_loss": float(losses.mean()) if len(losses) else 0.0, "profit_factor": float(pf),
            "median": float(np.median(R))}
