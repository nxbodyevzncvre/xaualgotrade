"""Wave metrics: fib ratios, durations, momentum, channels, alternation. All ATR-normalized."""
import numpy as np

RATIOS = [0.236, 0.382, 0.5, 0.618, 0.786, 1.0, 1.272, 1.618, 2.0, 2.618, 4.236]

def nearest_ratio(x, grid=RATIOS):
    return min(grid, key=lambda g: abs(g-x))

def impulse_features(imp, atr_at_confirm, durations):
    """durations: bars per wave [d1..d5]. Returns numeric feature dict."""
    f = {}
    f["w2_ret"] = imp["w2_ret"]; f["w4_ret"] = imp["w4_ret"]
    f["ext31"] = imp["ext31"]; f["ext51"] = imp["ext51"]
    f["w2_near"] = nearest_ratio(imp["w2_ret"]); f["w4_near"] = nearest_ratio(imp["w4_ret"])
    f["ext31_near"] = nearest_ratio(imp["ext31"]) if imp["ext31"] == imp["ext31"] else None
    f["truncated"] = int(imp["truncated"]); f["overlap"] = int(imp["overlap"])
    tot = float(sum(durations)) or 1.0
    f["dur_ratios"] = [d/tot for d in durations]
    f["alternation_depth"] = abs(imp["w2_ret"]-imp["w4_ret"])
    f["alternation_dur"] = abs(durations[1]-durations[3])/tot
    # momentum: ATR-normalized wave return / duration
    a = atr_at_confirm if atr_at_confirm and atr_at_confirm > 0 else 1.0
    f["mom_w1"] = imp["w1"]/a/max(durations[0],1)
    f["mom_w3"] = imp["w3"]/a/max(durations[2],1)
    f["mom_w5"] = imp["w5"]/a/max(durations[4],1)
    f["mom_decay"] = f["mom_w3"]-f["mom_w5"]
    return f

def channel_projection(p0, p1, p2):
    """W1->W2 channel: slope from p0->p1, parallel through p2. Returns width (price units)."""
    width = abs((p1-p0)-(p2-p1))
    return float(width)

def abc_features(abc):
    return {"kind": abc["kind"], "b_ret": abc["b_ret"], "b_near": nearest_ratio(abc["b_ret"]),
            "c_ext_a": abc["c_ext_a"], "c_near": nearest_ratio(abc["c_ext_a"])}
