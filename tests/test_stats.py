"""Stats guardrails: p-values must vary with data; FDR must be monotone-correct."""
import numpy as np
from statsx.permutation import permutation_diff_p, bh_fdr_real

def test_p_varies_with_data():
    rng = np.random.default_rng(0)
    a = rng.normal(0, 1, 200); b = rng.normal(2, 1, 200)
    p1, _ = permutation_diff_p(a, b, B=500)
    c = rng.normal(0, 1, 200); d = rng.normal(0, 1, 200)
    p2, _ = permutation_diff_p(c, d, B=500)
    assert p1 < 0.05, "separated groups must be significant"
    assert p2 > 0.05, "identical groups must not be significant"
    assert abs(p1-p2) > 0.05, "p-values constant across unrelated hypotheses"

def test_no_constant_p_family():
    rng = np.random.default_rng(1)
    ps = [permutation_diff_p(rng.normal(i % 2 * 1.5, 1, 100), rng.normal(0, 1, 100), B=300)[0] for i in range(6)]
    assert len(set(round(p, 4) for p in ps)) > 1, "family p-values are constant"

def test_fdr_monotone():
    q = bh_fdr_real([0.01, 0.04, 0.3, 0.9])
    assert all(q[i] <= q[i+1] for i in range(3)), "q must be non-decreasing in p order"
    assert q[0] <= 0.05 and q[-1] > 0.5
