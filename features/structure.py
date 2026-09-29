"""Market structure: HH/HL/LH/LL, trend/range states. Numeric only."""
import pandas as pd

def add_structure(df: pd.DataFrame, swings: pd.DataFrame, lookback_swings: int = 4) -> pd.DataFrame:
    df = df.copy()
    df["trend_state"] = 0  # -1 down, 0 range, +1 up; causal via confirm_idx
    if swings is None or len(swings) < 3:
        return df
    sw = swings.sort_values("confirm_idx").reset_index(drop=True)
    marks = {}  # confirm_idx -> state
    for i in range(3, len(sw)):
        w = sw.iloc[i-3:i+1]
        if len(w) < 3:
            continue
        # alternating high/low pattern check simplified: rising swing lows+highs => up
        highs = w[w.type == "high"].price.values
        lows = w[w.type == "low"].price.values
        s = 0
        if len(highs) >= 2 and len(lows) >= 2:
            if highs[-1] > highs[-2] and lows[-1] > lows[-2]:
                s = 1
            elif highs[-1] < highs[-2] and lows[-1] < lows[-2]:
                s = -1
        marks[int(w.iloc[-1].confirm_idx)] = s
    cur = 0
    mi = sorted(marks)
    j = 0
    states = []
    for idx in range(len(df)):
        while j < len(mi) and mi[j] <= idx:
            cur = marks[mi[j]]
            j += 1
        states.append(cur)
    df["trend_state"] = states
    return df
