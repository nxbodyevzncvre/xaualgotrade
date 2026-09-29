"""R6 ROUND 1 — intraday structure (prereg reports/PREREG_R6_INTRADAY.md).
Research 2020-22 -> validation 2023. 2024+ (final_test_data/) NEVER read.
Fixed exec for all cells: SL1.5/TP2R/24-bar, flat 21:00 UTC, costs 1x/2x/3x."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment

AGG = ROOT/"data"/"raw"/"_tickagg"
CELLS = ["ASIAN_BO", "ASIAN_FADE", "PDH_BO", "PDL_BO", "PDH_REJ", "PDL_REJ",
         "MOMO_london", "MOMO_overlap", "MOMO_ny", "MOMO_asian"]
SL_ATR, TP_R, MAX_HOLD = 1.5, 2.0, 24
SLIP = 0.15


def load_m1(split):
    m1 = pd.read_csv(ROOT/split/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
    m1["timestamp"] = pd.to_datetime(m1.timestamp, utc=True)
    wd = m1.timestamp.dt.weekday
    return m1[(wd < 5)].reset_index(drop=True)


def load_spread_m5(years):
    """M5 spread means from tick minute aggs (years restricted to <=2023)."""
    assert max(years) <= 2023, "FIREWALL: spread only for 2020-23"
    frames = []
    for y in years:
        for mo in range(1, 13):
            p = AGG/f"min_{y}{mo:02d}.csv"
            if p.exists():
                frames.append(pd.read_csv(p, parse_dates=["timestamp"]))
    if not frames:
        return None
    df = pd.concat(frames)
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    g = df.set_index("timestamp")
    sp = g.spread_mean.resample("5min").mean().dropna().reset_index()
    return sp.rename(columns={"spread_mean": "spread"})


def build_m5(m1):
    g = m1.set_index("timestamp")
    o = g.open.resample("5min").first(); h = g.high.resample("5min").max()
    l = g.low.resample("5min").min(); c = g.close.resample("5min").last()
    m5 = pd.DataFrame({"open": o, "high": h, "low": l, "close": c}).dropna().reset_index()
    hhr = m5.timestamp.dt.hour + m5.timestamp.dt.minute / 60
    m5["session"] = np.where(hhr < 7, "asian", np.where(hhr < 12, "london",
                       np.where(hhr < 14, "overlap", np.where(hhr < 17, "ny", "off"))))
    m5["date"] = m5.timestamp.dt.date
    tr = pd.concat([m5.high - m5.low, (m5.high - m5.close.shift(1)).abs(),
                    (m5.low - m5.close.shift(1)).abs()], axis=1).max(axis=1)
    m5["atr14"] = tr.rolling(14, min_periods=14).mean()
    m5["ret12"] = (m5.close - m5.close.shift(12)) / m5.atr14  # 12-bar momentum in ATR
    # causal tercile cutoffs from trailing 500-bar window
    roll = m5.ret12.rolling(500, min_periods=500)
    m5["q33"] = roll.quantile(1/3); m5["q67"] = roll.quantile(2/3)
    # daily levels from PRIOR completed UTC day (causal)
    d = m1.set_index("timestamp")
    dh = d.high.resample("D").max(); dl = d.low.resample("D").min(); dc = d.close.resample("D").last()
    dates = pd.to_datetime(m5.date).dt.tz_localize("UTC")
    m5["PDH"] = dates.map((dh.shift(1))); m5["PDL"] = dates.map((dl.shift(1)))
    m5["PDC"] = dates.map((dc.shift(1)))
    # asian range of the SAME date (known from 07:00 on; entries only after 07:00)
    asia = m5[m5.session == "asian"].groupby("date").agg(ah=("high", "max"), al=("low", "min"))
    m5["AH"] = m5.date.map(asia.ah); m5["AL"] = m5.date.map(asia.al)
    return m5


def detect(m5):
    """Fixed prereg event definitions. Returns {cell: DataFrame(timestamp, direction)}."""
    ev = {}
    ok = m5.atr14.notna() & (m5.atr14 > 0) & m5.PDH.notna() & m5.AH.notna()
    base = m5[ok].copy()
    hr = base.timestamp.dt.hour + base.timestamp.dt.minute / 60
    in_win = (hr >= 7) & (hr < 19)
    th = 0.1 * base.atr14
    # 1-2. asian range
    post = base[in_win & (hr >= 7)]
    th_post = 0.1 * post.atr14
    bo_l = post[post.close > post.AH + th_post].groupby("date").head(1)
    bo_s = post[post.close < post.AL - th_post].groupby("date").head(1)
    ev["ASIAN_BO"] = pd.concat([
        bo_l.assign(direction=1)[["timestamp", "direction"]],
        bo_s.assign(direction=-1)[["timestamp", "direction"]]])
    tch_h = post[(post.high >= post.AH) & (post.close < post.AH)]
    tch_l = post[(post.low <= post.AL) & (post.close > post.AL)]
    ev["ASIAN_FADE"] = pd.concat([
        tch_h.groupby("date").head(1).assign(direction=-1)[["timestamp", "direction"]],
        tch_l.groupby("date").head(1).assign(direction=1)[["timestamp", "direction"]]])
    # 3-6. prev-day levels
    ev["PDH_BO"] = base[in_win & (base.close > base.PDH + th)].assign(direction=1)[["timestamp", "direction"]]
    ev["PDL_BO"] = base[in_win & (base.close < base.PDL - th)].assign(direction=-1)[["timestamp", "direction"]]
    ev["PDH_REJ"] = base[in_win & (base.high >= base.PDH) & (base.close < base.PDH)].assign(direction=-1)[["timestamp", "direction"]]
    ev["PDL_REJ"] = base[in_win & (base.low <= base.PDL) & (base.close > base.PDL)].assign(direction=1)[["timestamp", "direction"]]
    # 7-10. session momentum terciles (fixed lookback 12, causal cutoffs)
    for sess in ["asian", "london", "overlap", "ny"]:
        s = base[(base.session == sess) & base.q33.notna()]
        long = s[s.ret12 > s.q67].assign(direction=1)[["timestamp", "direction"]]
        short = s[s.ret12 < s.q33].assign(direction=-1)[["timestamp", "direction"]]
        ev[f"MOMO_{sess}"] = pd.concat([long, short])
    for k in ev:
        ev[k] = ev[k].sort_values("timestamp").reset_index(drop=True)
    return ev


def backtest(m5, sig, spread_m5, spread_fallback, cost_mult=1.0,
             sl_atr=SL_ATR, tp_r=TP_R, max_hold=MAX_HOLD, flat_hour=21,
             entry_lo=7.0, entry_hi=19.0):
    """Fixed-R intraday backtest. Entry = open of bar after signal; flat flat_hour UTC.
    Defaults reproduce Round-1 exec exactly (Round 1 frozen); Round 2 passes overrides."""
    px = m5.set_index("timestamp")
    sp = None
    if spread_m5 is not None:
        sp = spread_m5.set_index("timestamp").spread
    closes = m5.close.values; opens = m5.open.values
    highs = m5.high.values; lows = m5.low.values
    atr = m5.atr14.values
    ts = m5.timestamp
    idx = {t: i for i, t in enumerate(ts)}
    R = []
    for _, s in sig.iterrows():
        i = idx.get(s.timestamp)
        if i is None or i + 1 >= len(m5):
            continue
        d = int(s.direction)
        e = i + 1
        hr_e = ts[e].hour + ts[e].minute / 60
        if hr_e < entry_lo or hr_e >= entry_hi or not np.isfinite(atr[e]) or atr[e] <= 0:
            continue
        entry = opens[e]
        risk = sl_atr * atr[e]
        sl = entry - d * risk
        tp = entry + d * tp_r * risk
        entry_date = ts[e].date()
        res = None
        exit_px, se, sx = entry, np.nan, np.nan
        if sp is not None:
            try:
                se = float(sp.loc[ts[e].floor("5min")])
            except KeyError:
                se = np.nan
        for k in range(e, min(e + max_hold, len(m5))):
            if ts[k].date() != entry_date or (ts[k].hour >= flat_hour):
                res = d * (closes[k] - entry) / risk
                exit_px = closes[k]
                break
            hit_tp = (highs[k] >= tp) if d == 1 else (lows[k] <= tp)
            hit_sl = (lows[k] <= sl) if d == 1 else (highs[k] >= sl)
            if hit_tp and hit_sl:
                res, exit_px = -1.0, sl
                break
            if hit_tp:
                res, exit_px = tp_r, tp
                break
            if hit_sl:
                res, exit_px = -1.0, sl
                break
        if res is None:
            j = min(e + max_hold - 1, len(m5) - 1)
            res, exit_px = d * (closes[j] - entry) / risk, closes[j]
        if sp is not None:
            try:
                sx = float(sp.loc[ts[min(e + max_hold - 1, len(m5) - 1)].floor("5min")])
            except KeyError:
                sx = np.nan
        se = se if np.isfinite(se) else spread_fallback
        sx = sx if np.isfinite(sx) else spread_fallback
        cost_R = cost_mult * (se + sx + 2 * SLIP) / 2 / risk
        R.append(res - cost_R)
    return np.array(R, float)


def stats(R):
    R = np.asarray(R, float)
    R = R[np.isfinite(R)]
    if len(R) == 0:
        return {"n": 0}
    m, lo, hi = bootstrap_mean_ci(R)
    w = float((R > 0).mean())
    wins = R[R > 0].mean() if (R > 0).any() else 0.0
    loss = R[R <= 0].mean() if (R <= 0).any() else 0.0
    pf = float(wins * w / abs(loss * (1 - w))) if loss < 0 else float("inf")
    eq = np.cumsum(R)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return {"n": int(len(R)), "exp_R": round(float(m), 4),
            "ci95": [round(float(lo), 4), round(float(hi), 4)],
            "win_rate": round(w, 4), "PF": round(pf, 4) if np.isfinite(pf) else None,
            "maxDD_R": round(dd, 2)}


def run_split(split, years):
    m1 = load_m1(split)
    m5 = build_m5(m1)
    sp5 = load_spread_m5(years)
    fall = float(sp5.spread.mean()) if sp5 is not None else 0.35
    return m5, sp5, fall


def evaluate(m5, sp5, fall, tag):
    ev = detect(m5)
    med_n = int(np.median([len(ev[c]) for c in CELLS]))
    rng = np.random.default_rng(0)
    pool = m5[(m5.timestamp.dt.hour >= 7) & (m5.timestamp.dt.hour < 19)].index.values
    ri = rng.choice(pool, size=min(med_n, len(pool)), replace=False)
    ev["RANDOM"] = pd.DataFrame({"timestamp": m5.timestamp.iloc[ri].reset_index(drop=True),
                                 "direction": rng.choice([-1, 1], size=len(ri))})
    out, P, Rs = {}, [], {}
    for cell in CELLS + ["RANDOM"]:
        r1 = backtest(m5, ev[cell], sp5, fall, 1.0)
        st = stats(r1)
        # cost sweeps: re-run at 2x/3x (exact, not approximated)
        e2 = float(np.nanmean(backtest(m5, ev[cell], sp5, fall, 2.0))) if len(r1) else None
        e3 = float(np.nanmean(backtest(m5, ev[cell], sp5, fall, 3.0))) if len(r1) else None
        st["exp_R_2x"] = round(e2, 4) if e2 is not None and np.isfinite(e2) else None
        st["exp_R_3x"] = round(e3, 4) if e3 is not None and np.isfinite(e3) else None
        out[cell] = st
        Rs[cell] = r1
    for cell in CELLS:
        a, b = Rs[cell], Rs["RANDOM"]
        a = a[np.isfinite(a)]; b = b[np.isfinite(b)]
        if len(a) >= 100 and len(b) >= 30:
            p, diff = permutation_diff_p(a, b)
        else:
            p, diff = 1.0, 0.0
        out[cell]["perm_p_vs_random"] = round(float(p), 4)
        out[cell]["diff_vs_random"] = round(float(diff), 4)
        P.append(float(p) if out[cell]["n"] >= 100 else 1.0)
    q = bh_fdr_real(P)
    for k, qq in zip(CELLS, q):
        out[k]["q"] = round(float(qq), 4)
    return out


def main():
    out = {"prereg": "R6-intraday round1; fixed SL1.5/TP2R/24b flat21UTC; costs 1x/2x/3x",
           "research": {}, "validation": {}, "walkforward": {}}
    m5r, sp5r, fallr = run_split("research_data", [2020, 2021, 2022])
    out["research"] = evaluate(m5r, sp5r, fallr, "research")
    print("research done", flush=True)
    m5v, sp5v, fallv = run_split("validation_data", [2023])
    out["validation"] = evaluate(m5v, sp5v, fallv, "validation")
    print("validation done", flush=True)
    # walk-forward on bid M1 year slices (spread fallback = slice mean tick or 0.35)
    m1all = pd.concat([load_m1("research_data"), load_m1("validation_data")]).sort_values("timestamp")
    yrs = m1all.timestamp.dt.year.values
    for tr, te in [([2020], [2021]), ([2020, 2021], [2022]), ([2020, 2021, 2022], [2023])]:
        sub = m1all[np.isin(yrs, te)].reset_index(drop=True)
        m5t = build_m5(sub)
        sp = load_spread_m5(te)
        f = float(sp.spread.mean()) if sp is not None else 0.35
        ev = detect(m5t)
        wf = {}
        for cell in CELLS:
            r = backtest(m5t, ev[cell], sp, f, 1.0)
            st = stats(r)
            wf[cell] = {"n": st.get("n", 0), "exp_R": st.get("exp_R"),
                        "ci95": st.get("ci95")}
        out["walkforward"][f"{tr}->{te}"] = wf
    print("walkforward done", flush=True)
    with open(ROOT/"reports"/"intraday_r6.json", "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    log_experiment({"hypothesis": "R6 round1 intraday structure", "dataset": "research 2020-22 -> validation 2023",
                    "results": {"cells": CELLS}, "status": "REJECTED"})
    for split in ["research", "validation"]:
        print(f"== {split} ==", flush=True)
        for c in CELLS + ["RANDOM"]:
            s = out[split][c]
            print(f"{c:12s} n={s.get('n')} exp={s.get('exp_R')} ci={s.get('ci95')} "
                  f"1x/2x/3x={s.get('exp_R')}/{s.get('exp_R_2x')}/{s.get('exp_R_3x')} "
                  f"p={s.get('perm_p_vs_random')} q={s.get('q')}", flush=True)
    return out


if __name__ == "__main__":
    main()
