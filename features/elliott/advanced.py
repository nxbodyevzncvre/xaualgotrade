"""E2 advanced structures: diagonals, triangles (4 kinds), partial waves, invalidation.
All causal; classification strictly before outcome window."""
import pandas as pd
import numpy as np

def _slopes(p_highs, p_lows, idx_highs, idx_lows):
    import numpy as _np
    sh = float(_np.polyfit(idx_highs, p_highs, 1)[0]) if len(p_highs) >= 2 else 0.0
    sl = float(_np.polyfit(idx_lows, p_lows, 1)[0]) if len(p_lows) >= 2 else 0.0
    return sh, sl

def diagonal_candidates(swings: pd.DataFrame, atr: pd.Series):
    """Overlap + converging trendlines + shrinking width. Returns dicts (no leading/ending split:
    position-in-larger-structure unknown without subjective count -> single diagonal-like class)."""
    from features.elliott.waves import find_impulses
    out = []
    for im in find_impulses(swings):
        if not im["overlap"]:
            continue
        p = np.array(im["prices"])
        ci = int(im["confirm_idx"])
        a = float(atr.iloc[ci]) if ci < len(atr) and np.isfinite(atr.iloc[ci]) else 1.0
        highs = [p[1], p[3], p[5]]; lows = [p[0], p[2], p[4]]
        sh, sl = _slopes(highs, lows, [1, 3, 5], [0, 2, 4])
        converging = bool(sh < sl) if im["direction"] == 1 else bool(sh < sl)
        width_start = abs(p[1]-p[0])/a; width_end = abs(p[5]-p[4])/a
        shrinking = bool(width_end < width_start)
        if converging and shrinking:
            out.append({"confirm_idx": ci, "direction": im["direction"],
                        "width_start": width_start, "width_end": width_end,
                        "sh": sh, "sl": sl, "prices": im["prices"]})
    return out

def generic_converging(swings: pd.DataFrame, atr: pd.Series):
    """Null: any 6 alternating swings with shrinking ranges (no impulse progress rules)."""
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    out = []
    for i in range(len(sw)-5):
        w = sw.iloc[i:i+6]
        t = w.type.tolist()
        if t not in (["low","high"]*3, ["high","low"]*3):
            continue
        p = w.price.values; ci = int(w.confirm_idx.iloc[-1])
        a = float(atr.iloc[ci]) if ci < len(atr) and np.isfinite(atr.iloc[ci]) else 1.0
        r = [abs(p[k+1]-p[k])/a for k in range(5)]
        if all(r[k] > r[k+1] for k in range(4)):
            d = 1 if t[0] == "low" and p[-1] > p[0] else (-1 if t[0] == "high" and p[-1] < p[0] else 0)
            out.append({"confirm_idx": ci, "direction": d, "ranges": r})
    return out

def triangle_candidates(swings: pd.DataFrame, atr: pd.Series):
    """Contracting / barrier / expanding / running — causal, pre-breakout. Running often ambiguous -> flagged."""
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    out = []
    for i in range(len(sw)-5):
        w = sw.iloc[i:i+6].reset_index(drop=True)
        t = w.type.tolist()
        if t not in (["low","high"]*3, ["high","low"]*3):
            continue
        p = w.price.values.astype(float); ci = int(w.confirm_idx.iloc[-1])
        a = float(atr.iloc[ci]) if ci < len(atr) and np.isfinite(atr.iloc[ci]) else 1.0
        if a <= 0 or not np.isfinite(a):
            continue
        highs = p[1::2] if t[0] == "low" else p[0::2]
        lows = p[0::2] if t[0] == "low" else p[1::2]
        rngs = np.array([abs(p[k+1]-p[k]) for k in range(5)])
        h_range = highs.max()-highs.min(); l_range = lows.max()-lows.min()
        flat_top = bool(h_range <= 0.5*a); flat_bot = bool(l_range <= 0.5*a)
        rising_lows = bool(lows[-1] > lows[0]); falling_highs = bool(highs[-1] < highs[0])
        expanding = bool(all(rngs[k] < rngs[k+1] for k in range(4)))
        contracting = bool(all(rngs[k] > rngs[k+1] for k in range(4)))
        kind = None
        if contracting and not flat_top and not flat_bot:
            kind = "contracting"
        elif (flat_top and rising_lows) or (flat_bot and falling_highs):
            kind = "barrier"
        elif expanding:
            kind = "expanding"
        elif abs(p[1]-p[0]) > 0 and abs(p[3]-p[1]) > abs(p[1]-p[0]):
            kind = "running_suspect"
        if kind:
            out.append({"start": i, "confirm_idx": ci, "kind": kind,
                        "hi": float(highs.max()), "lo": float(lows.min()),
                        "prices": [float(x) for x in p]})
    return out

def partial_prefixes(swings: pd.DataFrame):
    """E2-F: impulse prefixes (3 swings=1-2, 4 swings=1-2-3start, 5 swings), ABC prefix (3 swings A-B),
    triangle prefix (4-5 swings A-B-C[-D]). Features use only swings up to prefix confirm."""
    from features.elliott.waves import find_impulses, find_abc
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    pref = []
    for i in range(len(sw)-2):
        w3 = sw.iloc[i:i+3]
        t = w3.type.tolist()
        if t in (["low","high","low"], ["high","low","high"]):
            p = w3.price.values; legA = abs(p[1]-p[0])
            if legA > 0 and 0 < abs(p[2]-p[1])/legA < 1:
                pref.append({"kind": "1-2", "end": i+2, "confirm_idx": int(w3.confirm_idx.iloc[-1])})
    for i in range(len(sw)-3):
        w4 = sw.iloc[i:i+4]
        t = w4.type.tolist()
        if t in (["low","high","low","high"], ["high","low","high","low"]):
            pref.append({"kind": "A-B", "end": i+3, "confirm_idx": int(w4.confirm_idx.iloc[-1])})
            pref.append({"kind": "1-2-3start", "end": i+3, "confirm_idx": int(w4.confirm_idx.iloc[-1])})
    for i in range(len(sw)-4):
        w5 = sw.iloc[i:i+5]
        t = w5.type.tolist()
        if t in (["low","high","low","high","low"], ["high","low","high","low","high"]):
            pref.append({"kind": "tri-A-B-C-D", "end": i+4, "confirm_idx": int(w5.confirm_idx.iloc[-1])})
    return pref

def invalidation_events(swings: pd.DataFrame, df: pd.DataFrame):
    """E2-G: W2/W4/ABC/triangle invalidation as price events after prefix confirm, before completion+20 bars.
    Each event: kind, event_idx (causal), direction of prior structure."""
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    close, high, low = df.close.values, df.high.values, df.low.values
    n = len(df)
    evs = []
    for i in range(len(sw)-2):
        w = sw.iloc[i:i+3].reset_index(drop=True)
        t = w.type.tolist()
        if t not in (["low","high","low"], ["high","low","high"]):
            continue
        p = w.price.values; ci = int(w.confirm_idx.iloc[-1])
        bull = t[0] == "low"
        inv_level = p[0]  # W2 invalidation: beyond wave-1 origin
        for k in range(ci+1, min(ci+21, n)):
            hit = (low[k] <= inv_level) if bull else (high[k] >= inv_level)
            if hit:
                evs.append({"kind": "W2_invalidation", "event_idx": k,
                            "direction": 1 if bull else -1})
                break
    for i in range(len(sw)-4):
        w = sw.iloc[i:i+5].reset_index(drop=True)
        t = w.type.tolist()
        if t not in (["low","high","low","high","low"], ["high","low","high","low","high"]):
            continue
        p = w.price.values; ci = int(w.confirm_idx.iloc[-1])
        bull = t[0] == "low"
        w1top = p[1]  # W4 invalidation: overlap into wave-1 extreme
        for k in range(ci+1, min(ci+21, n)):
            hit = (low[k] <= w1top) if bull else (high[k] >= w1top)
            if hit:
                evs.append({"kind": "W4_invalidation", "event_idx": k,
                            "direction": 1 if bull else -1})
                break
    return evs

def generic_swing_failure(swings: pd.DataFrame, df: pd.DataFrame):
    """Null for E2-G: any swing extreme breached within 20 bars after confirm (no Elliott label)."""
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    high, low = df.high.values, df.low.values
    n = len(df)
    evs = []
    for _, r in sw.iterrows():
        ci = int(r.confirm_idx); px = float(r.price)
        bull = r.type == "low"
        for k in range(ci+1, min(ci+21, n)):
            hit = (low[k] <= px) if bull else (high[k] >= px)
            if hit:
                evs.append({"kind": "generic_swing_fail", "event_idx": k,
                            "direction": 1 if bull else -1})
                break
    return evs
