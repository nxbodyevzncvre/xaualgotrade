"""Null models for Elliott falsification (23.31): surrogate swings + bootstrap returns."""
import numpy as np
import pandas as pd

def surrogate_swings(swings: pd.DataFrame, seed=0):
    """Shuffle swing returns: preserves count + marginal sizes, destroys sequencing (incl. Elliott order)."""
    rng = np.random.default_rng(seed)
    sw = swings.sort_values("confirm_idx").reset_index(drop=True).copy()
    rets = np.array(sw.price.diff().dropna().values)
    rng.shuffle(rets)
    px = [sw.price.iloc[0]]
    for r in rets:
        px.append(px[-1]+r)
    sw["price"] = px
    # re-derive alternating types from shuffled direction (keeps causality of confirms)
    types = []
    for k in range(len(sw)):
        if k == 0:
            types.append(sw.type.iloc[0])
        else:
            types.append("high" if px[k] > px[k-1] else "low")
    sw["type"] = types
    return sw

def bootstrap_returns(close: pd.Series, seed=0):
    """IID bootstrap of returns -> surrogate price path (destroys autocorrelation/waves)."""
    rng = np.random.default_rng(seed)
    r = close.pct_change().dropna().values
    rb = rng.choice(r, size=len(r), replace=True)
    px = [close.iloc[0]]
    for x in rb:
        px.append(px[-1]*(1+x))
    return pd.Series(px, index=close.index)
