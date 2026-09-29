"""Fixed-R backtest: entry at signal bar close, SL/TP in R, time stop, costs."""
import pandas as pd
import numpy as np

def backtest_signals(df: pd.DataFrame, signals: pd.DataFrame, sl_atr=1.5, tp_R=2.0,
                     max_hold=20, spread=0.35, slippage=0.15) -> pd.DataFrame:
    """signals columns: idx (entry bar), direction (+1/-1). Costs in price units."""
    cost = spread + slippage
    o, h, l, c, a = df.open.values, df.high.values, df.low.values, df.close.values, df.atr.values
    n = len(df)
    trades = []
    for _, s in signals.iterrows():
        i = int(s.idx)
        if i + 1 >= n:
            continue
        d = int(s.direction)
        atrv = a[i]
        if not np.isfinite(atrv) or atrv <= 0:
            continue
        entry = c[i] + d * cost / 2  # pay half cost on entry, half on exit approx -> full cost drag
        sl = entry - d * sl_atr * atrv
        tp = entry + d * tp_R * sl_atr * atrv
        risk = abs(entry - sl)
        if risk <= 0:
            continue
        res, mfe, mae = None, 0.0, 0.0
        exit_px = c[min(i+max_hold, n-1)] - d * cost / 2
        for k in range(1, max_hold+1):
            j = i + k
            if j >= n:
                break
            mfe = max(mfe, d*(h[j]-entry)/risk if d == 1 else d*(entry-l[j])/risk)
            mae = min(mae, d*(l[j]-entry)/risk if d == 1 else d*(entry-h[j])/risk)
            hit_tp = (h[j] >= tp) if d == 1 else (l[j] <= tp)
            hit_sl = (l[j] <= sl) if d == 1 else (h[j] >= sl)
            if hit_tp and hit_sl:
                res = -1.0  # conservative: stop first on ambiguity
                exit_px = sl
                break
            if hit_tp:
                res = tp_R
                exit_px = tp
                break
            if hit_sl:
                res = -1.0
                exit_px = sl
                break
        if res is None:
            res = d*(exit_px-entry)/risk
        # forward returns in R
        fwd = {}
        for nb in [1, 5, 10, 20]:
            j = min(i+nb, n-1)
            fwd[f"ret_{nb}R"] = d*(c[j]-entry)/risk
        trades.append({"entry_idx": i, "direction": d, "entry": entry, "sl": sl, "tp": tp,
                       "R": float(res), "MFE": float(mfe), "MAE": float(mae), **fwd})
    return pd.DataFrame(trades)
