"""Fibonacci retracement construction + reaction measurement (causal)."""
import pandas as pd
import numpy as np

LEVELS = [0.236, 0.382, 0.5, 0.618, 0.786]

def pairs_to_retracements(swings: pd.DataFrame) -> pd.DataFrame:
    """Consecutive alternating swings -> retracement grid known at later confirm_idx."""
    if swings is None or len(swings) < 2:
        return pd.DataFrame()
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    rows = []
    for i in range(1, len(sw)):
        a, b = sw.iloc[i-1], sw.iloc[i]
        if a.type == b.type:
            continue
        lo, hi = (a.price, b.price) if a.type == "low" else (b.price, a.price)
        rng = hi - lo
        if rng <= 0:
            continue
        known = int(max(a.confirm_idx, b.confirm_idx))
        rows.append({"pair": i, "confirm_idx": known, "lo": float(lo), "hi": float(hi),
                     "range": float(rng), "direction": "up" if a.type == "low" else "down"})
    return pd.DataFrame(rows)

def level_price(lo: float, hi: float, lvl: float, direction: str) -> float:
    return hi - (hi-lo)*lvl if direction == "up" else lo + (hi-lo)*lvl

def measure_reactions(df: pd.DataFrame, pairs: pd.DataFrame, levels=LEVELS,
                      tol_atr: float = 0.25, fwd: int = 10, rev_atr: float = 0.25,
                      rng_seed: int = 42) -> pd.DataFrame:
    """For each pair+level: touched within fwd bars after confirm? reversed by rev_atr?
    Control: same geometry with randomized level ~ U(0.1,0.9)."""
    rng = np.random.default_rng(rng_seed)
    close, high, low, atrv = df.close.values, df.high.values, df.low.values, df.atr.values
    n = len(df)
    recs = []
    for _, p in pairs.iterrows():
        c0 = int(p.confirm_idx)
        if c0 + fwd >= n:
            continue
        a = atrv[c0]
        if not np.isfinite(a) or a <= 0:
            continue
        for lvl in levels:
            lp = level_price(p.lo, p.hi, lvl, p.direction)
            touched, reacted = False, False
            for k in range(1, fwd+1):
                i = c0 + k
                if abs(low[i]-lp) <= tol_atr*a or abs(high[i]-lp) <= tol_atr*a or (low[i] <= lp <= high[i]):
                    touched = True
                    # reversal: close moves rev_atr away from level against approach direction
                    base = close[c0]
                    side = 1 if base < lp else -1  # price below level expects resistance
                    for j in range(i, min(i+fwd, n)):
                        if side == 1 and (lp - close[j]) >= rev_atr*a:
                            reacted = True
                            break
                        if side == -1 and (close[j] - lp) >= rev_atr*a:
                            reacted = True
                            break
                    break
            recs.append({"pair": p.pair, "confirm_idx": c0, "level": lvl, "kind": "fib",
                         "touched": touched, "reacted": reacted and touched})
        # one matched random control per pair
        rl = float(rng.uniform(0.1, 0.9))
        lp = level_price(p.lo, p.hi, rl, p.direction)
        touched, reacted = False, False
        for k in range(1, fwd+1):
            i = c0 + k
            if abs(low[i]-lp) <= tol_atr*a or abs(high[i]-lp) <= tol_atr*a or (low[i] <= lp <= high[i]):
                touched = True
                base = close[c0]
                side = 1 if base < lp else -1
                for j in range(i, min(i+fwd, n)):
                    if side == 1 and (lp - close[j]) >= rev_atr*a:
                        reacted = True
                        break
                    if side == -1 and (close[j] - lp) >= rev_atr*a:
                        reacted = True
                        break
                break
        recs.append({"pair": p.pair, "confirm_idx": c0, "level": rl, "kind": "random", "touched": touched,
                     "reacted": reacted and touched})
    return pd.DataFrame(recs)
