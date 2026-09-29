"""Real inference primitives. All p-values computed from observed data. No defaults."""
import numpy as np

def permutation_diff_p(x, y, B=2000, seed=0):
    """Two-sided permutation p for difference in means of x vs y."""
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float); y = np.asarray(y, float)
    x = x[np.isfinite(x)]; y = y[np.isfinite(y)]
    if len(x) < 5 or len(y) < 5:
        return 1.0, 0.0
    obs = x.mean()-y.mean()
    pool = np.concatenate([x, y])
    c = 0
    for _ in range(B):
        rng.shuffle(pool)
        if abs(pool[:len(x)].mean()-pool[len(x):].mean()) >= abs(obs):
            c += 1
    return (c+1)/(B+1), obs

def bootstrap_mean_ci(x, B=2000, ci=0.95, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) == 0:
        return float("nan"), float("nan"), float("nan")
    bs = [rng.choice(x, size=len(x), replace=True).mean() for _ in range(B)]
    return float(x.mean()), float(np.quantile(bs, (1-ci)/2)), float(np.quantile(bs, 1-(1-ci)/2))

def bh_fdr_real(pvals):
    p = np.asarray(pvals, float)
    n = len(p); order = np.argsort(p)
    q = np.empty(n); prev = 1.0
    for rank, idx in enumerate(reversed(order), start=1):
        prev = min(prev, p[idx]*n/(n-rank+1))
        q[idx] = prev
    return q
