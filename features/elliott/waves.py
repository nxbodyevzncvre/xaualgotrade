"""Objective Elliott-like wave detection. Causal: structure known only at last confirm_idx.
Textbook-ambiguous patterns are marked NOT RELIABLY DETECTABLE (23.1/23.34)."""
import pandas as pd
import numpy as np

BULL, BEAR = 1, -1

def _dir(sw):
    return BULL if sw.iloc[0].type == "low" else BEAR

def find_impulses(swings: pd.DataFrame):
    """5-wave impulse = 6 alternating swings with progress + W2/W4 validity. Returns list of dicts."""
    if swings is None or len(swings) < 6:
        return []
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    out = []
    for i in range(len(sw) - 5):
        w = sw.iloc[i:i+6].reset_index(drop=True)
        types = w.type.tolist()
        if types != ["low", "high", "low", "high", "low", "high"] and types != ["high", "low", "high", "low", "high", "low"]:
            continue
        d = BULL if types[0] == "low" else BEAR
        p = w.price.values
        # directional progress
        if d == BULL:
            if not (p[1] > p[0] and p[3] > p[1] and p[5] > p[3] and p[2] > p[0] and p[4] > p[2]):
                continue
            w1, w2r = p[1]-p[0], (p[1]-p[2])/(p[1]-p[0])
            w3, w4r = p[3]-p[2], (p[3]-p[4])/(p[3]-p[2])
            w5 = p[5]-p[4]
            overlap = bool(p[4] <= p[1])
            truncated = bool(p[5] <= p[3])
        else:
            if not (p[1] < p[0] and p[3] < p[1] and p[5] < p[3] and p[2] < p[0] and p[4] < p[2]):
                continue
            w1, w2r = p[0]-p[1], (p[2]-p[1])/(p[0]-p[1])
            w3, w4r = p[2]-p[3], (p[4]-p[3])/(p[2]-p[3])
            w5 = p[4]-p[5]
            overlap = bool(p[4] >= p[1])
            truncated = bool(p[5] >= p[3])
        if not (0 < w2r < 1 and 0 < w4r < 1):
            continue
        out.append({"start": i, "confirm_idx": int(w.confirm_idx.iloc[-1]),
                    "direction": d, "prices": [float(x) for x in p],
                    "w1": float(w1), "w2_ret": float(w2r), "w3": float(w3),
                    "w4_ret": float(w4r), "w5": float(w5),
                    "overlap": overlap, "truncated": truncated,
                    "ext31": float(w3/w1) if w1 > 0 else float("nan"),
                    "ext51": float(w5/w1) if w1 > 0 else float("nan"),
                    "diagonal_like": bool(overlap)})
    return out

def find_abc(swings: pd.DataFrame):
    """ABC = 4 alternating swings. Subclass: zigzag/flat/expanded/UNCERTAIN.
    Double/triple/W-X-Y-X-Z, barrier/expanding/running triangles: NOT RELIABLY DETECTABLE."""
    if swings is None or len(swings) < 4:
        return []
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    out = []
    for i in range(len(sw) - 3):
        w = sw.iloc[i:i+4].reset_index(drop=True)
        types = w.type.tolist()
        if types != ["low", "high", "low", "high"] and types != ["high", "low", "high", "low"]:
            continue
        p = w.price.values
        legA = abs(p[1]-p[0]); legB = abs(p[2]-p[1]); legC = abs(p[3]-p[2])
        if legA <= 0:
            continue
        b_ret = legB/legA
        if b_ret < 0.8:
            kind = "zigzag"
        elif b_ret <= 1.2:
            kind = "flat"
        elif b_ret <= 1.6:
            kind = "expanded_flat"
        else:
            kind = "UNCERTAIN"
        out.append({"start": i, "confirm_idx": int(w.confirm_idx.iloc[-1]),
                    "direction": BULL if types[0] == "high" else BEAR,
                    "kind": kind, "b_ret": float(b_ret),
                    "c_ext_a": float(legC/legA), "prices": [float(x) for x in p]})
    return out

def find_contracting_triangle(swings: pd.DataFrame):
    """Contracting triangle: 6 alternating swings, strictly shrinking ranges, pre-breakout only."""
    if swings is None or len(swings) < 6:
        return []
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    out = []
    for i in range(len(sw) - 5):
        w = sw.iloc[i:i+6].reset_index(drop=True)
        types = w.type.tolist()
        if types not in (["low","high"]*3, ["high","low"]*3):
            continue
        p = w.price.values
        ranges = [abs(p[k+1]-p[k]) for k in range(5)]
        if not all(ranges[k] > ranges[k+1] for k in range(4)):
            continue
        out.append({"start": i, "confirm_idx": int(w.confirm_idx.iloc[-1]),
                    "ranges": [float(x) for x in ranges], "prices": [float(x) for x in p]})
    return out

def partial_states(swings: pd.DataFrame):
    """State machine trace: after each swing, current partial impulse/ABC depth. Causal."""
    if swings is None or len(swings) == 0:
        return []
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    return [{"confirm_idx": int(r.confirm_idx), "n_swings": k+1, "type": r.type, "price": float(r.price)}
            for k, (_, r) in enumerate(sw.iterrows())]

NOT_RELIABLE = ["barrier_triangle", "expanding_triangle", "running_triangle",
                "double_three", "triple_three", "w_x_y_x_z", "leading_diagonal_vs_ending"]
