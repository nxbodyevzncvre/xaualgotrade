"""R6 ROUND 3 — VWAP/EMA reversion probes + rejection single-filter info (prereg PREREG_R6_ROUND3.md).
Research 2020-22 -> validation 2023. 2024+ NEVER read. No combos, no Fib, no ML."""
import json, sys
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from research import run_intraday_r6 as R6
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment

EXEC = dict(sl_atr=1.0, tp_r=1.0, max_hold=12, flat_hour=21)
BUCKETS = [(0.5, 1.0), (1.0, 1.5), (1.5, 2.0), (2.0, np.inf)]


def add_anchors(m1, m5):
    """Session VWAP (typical x tick_volume, UTC-day reset) + EMA20, mapped to M5."""
    d = m1.set_index("timestamp")
    tp = (d.high + d.low + d.close) / 3
    day = d.index.floor("D")
    cum_pv = (tp * d.tick_volume).groupby(day).cumsum()
    cum_v = d.tick_volume.groupby(day).cumsum()
    vwap_m1 = (cum_pv / cum_v).rename("vwap")
    m5 = m5.merge(vwap_m1.reset_index().groupby(pd.Grouper(key="timestamp", freq="5min")).last(),
                  left_on="timestamp", right_on="timestamp", how="left")
    m5["ema20"] = m5.close.ewm(span=20, min_periods=20).mean()
    m5["z_vwap"] = (m5.close - m5.vwap) / m5.atr14
    m5["z_ema"] = (m5.close - m5.ema20) / m5.atr14
    # daily open (causal: today's open known after 00:00)
    do = d.open.resample("D").first()
    m5["DOPEN"] = pd.to_datetime(m5.date).dt.tz_localize("UTC").map(do)
    m5["dist_open"] = (m5.close - m5.DOPEN).abs() / m5.atr14
    # vol regime: RV48 trailing-1000 quantile thirds
    rv = m5.close.pct_change().rolling(48, min_periods=48).std()
    m5["vol_q"] = rv.rolling(1000, min_periods=1000).rank(pct=True)
    m5["vol_reg"] = pd.cut(m5.vol_q, [0, 1/3, 2/3, 1.0], labels=["LOW", "NORM", "HIGH"])
    # rejection-bar body/range
    m5["body_rng"] = (m5.close - m5.open).abs() / (m5.high - m5.low + 1e-12)
    return m5


def d1_cells(m5):
    """16 probe cells: {vwap,ema} x 4 buckets x 2 sides. Fade direction = toward anchor."""
    cells = {}
    ok = m5.atr14.notna() & (m5.atr14 > 0)
    hr = m5.timestamp.dt.hour + m5.timestamp.dt.minute / 60
    base = m5[ok & (hr >= 7) & (hr < 19)]
    for anchor in ["vwap", "ema"]:
        z = base[f"z_{anchor}"].copy()
        for i, (lo, hi) in enumerate(BUCKETS):
            for side, sgn in [("above", 1), ("below", -1)]:
                m = (z * sgn >= lo) & (z * sgn < hi) & z.notna()
                sig = base[m].assign(direction=-sgn)[["timestamp", "direction"]]
                cells[f"{anchor.upper()}_{lo}_{hi}_{side}"] = sig.reset_index(drop=True)
    return cells


def probe_return(m5, sig, bars=12):
    """P(close reaches halfway back to anchor used at signal) — descriptive."""
    return None  # computed per-anchor in evaluate via vector ops


def d2_cells(m5):
    """Base first-of-day rejection + 13 single-filter sub-cells (no combos)."""
    ok = m5.atr14.notna() & (m5.atr14 > 0) & m5.PDH.notna() & m5.DOPEN.notna()
    base = m5[ok].copy()
    hr = base.timestamp.dt.hour + base.timestamp.dt.minute / 60
    win = (hr >= 7) & (hr < 19)
    rej_h = base[win & (base.high >= base.PDH) & (base.close < base.PDH)].copy()
    rej_h["direction"] = -1
    rej_h["wick"] = (rej_h.high - rej_h.PDH) / rej_h.atr14
    rej_l = base[win & (base.low <= base.PDL) & (base.close > base.PDL)].copy()
    rej_l["direction"] = 1
    rej_l["wick"] = (rej_l.PDL - rej_l.low) / rej_l.atr14
    rej = pd.concat([rej_h, rej_l]).sort_values("timestamp")
    rej = rej.groupby("date").head(2)  # first touch per side per day max
    cells = {"REJ_BASE": rej[["timestamp", "direction"]].reset_index(drop=True)}
    # F1 magnitude
    cells["REJ_mag_hi"] = rej[rej.wick > 0.5][["timestamp", "direction"]].reset_index(drop=True)
    cells["REJ_mag_lo"] = rej[rej.wick <= 0.5][["timestamp", "direction"]].reset_index(drop=True)
    # F2 vol regime
    for v in ["LOW", "NORM", "HIGH"]:
        cells[f"REJ_vol_{v}"] = rej[rej.vol_reg.astype(str) == v][["timestamp", "direction"]].reset_index(drop=True)
    # F3 distance from open
    cells["REJ_far"] = rej[rej.dist_open > 1.0][["timestamp", "direction"]].reset_index(drop=True)
    cells["REJ_near"] = rej[rej.dist_open <= 1.0][["timestamp", "direction"]].reset_index(drop=True)
    # F4 session
    for s in ["london", "overlap", "ny"]:
        cells[f"REJ_{s}"] = rej[rej.session == s][["timestamp", "direction"]].reset_index(drop=True)
    # F5 reclaim speed: 1 bar vs 2-3 (needs prior-bar context: recompute causal)
    # F5 reclaim speed: pierce bar -> first close back inside within 3 bars.
    # speed 1 = same bar; 2-3 = later bar (causal, timestamp = reclaim bar).
    spd1, spd23 = [], []
    for side, col, is_res in [("h", base.PDH, True), ("l", base.PDL, False)]:
        pierce = base[win & (base.high >= col)] if is_res else base[win & (base.low <= col)]
        closes = base.close.values
        idxpos = {t: k for k, t in enumerate(base.timestamp)}
        for _, row in pierce.iterrows():
            k = idxpos[row.timestamp]
            lvl = row.PDH if is_res else row.PDL
            d = -1 if is_res else 1
            for j in range(k, min(k + 3, len(base))):
                r2 = base.iloc[j]
                if r2.date != row.date:
                    break
                inside = (r2.close < lvl) if is_res else (r2.close > lvl)
                if inside:
                    (spd1 if j == k else spd23).append({"timestamp": r2.timestamp, "direction": d})
                    break
    spd1 = pd.DataFrame(spd1)
    spd23 = pd.DataFrame(spd23)
    if len(spd1):
        spd1 = spd1.sort_values("timestamp").groupby(spd1.timestamp.dt.date).head(2)
    if len(spd23):
        spd23 = spd23.sort_values("timestamp").groupby(spd23.timestamp.dt.date).head(2)
    cols = ["timestamp", "direction"]
    cells["REJ_speed_1"] = spd1[cols].reset_index(drop=True) if len(spd1) else pd.DataFrame({c: [] for c in cols})
    cells["REJ_speed_23"] = spd23[cols].reset_index(drop=True) if len(spd23) else pd.DataFrame({c: [] for c in cols})
    # F6 body/range
    cells["REJ_body_hi"] = rej[rej.body_rng > 0.5][["timestamp", "direction"]].reset_index(drop=True)
    cells["REJ_body_lo"] = rej[rej.body_rng <= 0.5][["timestamp", "direction"]].reset_index(drop=True)
    return cells, rej


def evaluate(m5, sp5, fall, anchor_close):
    """anchor_close: dict cell->anchor series name for P(return) calc."""
    d1 = d1_cells(m5)
    d2, rej = d2_cells(m5)
    out, P, Rs = {}, [], {}
    # D1 probes
    for cell, sig in d1.items():
        anchor = "vwap" if cell.startswith("VWAP") else "ema20"
        r1 = R6.backtest(m5, sig, sp5, fall, 1.0, **EXEC)
        st = R6.stats(r1)
        e2 = float(np.nanmean(R6.backtest(m5, sig, sp5, fall, 2.0, **EXEC))) if len(r1) else None
        st["exp_R_2x"] = round(e2, 4) if e2 is not None and np.isfinite(e2) else None
        # P(return halfway): vectorized over M5 frame
        px = m5.set_index("timestamp")
        a = px[anchor]; c = px.close
        fwd = pd.DataFrame({b: c.shift(-b) for b in range(1, 13)})
        dist0 = (c - a).abs()
        sig_ts = sig.timestamp
        hit, mfe, mae = [], [], []
        atr = px.atr14
        for t in sig_ts:
            if t not in px.index:
                continue
            d0 = dist0.loc[t]
            if not np.isfinite(d0) or d0 <= 0:
                continue
            seg = fwd.loc[t].values
            tgt = a.loc[t]
            path = np.abs(seg - tgt).min() if np.isfinite(seg).any() else np.nan
            hit.append(float(path <= d0 / 2))
            at = atr.loc[t]
            f = seg - c.loc[t]
            sgn = -np.sign(c.loc[t] - tgt)  # fade direction
            mfe.append(float((sgn * f).max() / at) if np.isfinite(at) and at > 0 else np.nan)
            mae.append(float((sgn * f).min() / at) if np.isfinite(at) and at > 0 else np.nan)
        hit = np.array(hit)
        st["P_return_half"] = round(float(np.nanmean(hit)), 4) if len(hit) else None
        st["MFE_atr"] = round(float(np.nanmean(mfe)), 4) if len(mfe) else None
        st["MAE_atr"] = round(float(np.nanmean(mae)), 4) if len(mae) else None
        out[cell] = st
        Rs[cell] = r1
    # matched random for D1 (same 07-19 pool)
    rng = np.random.default_rng(7)
    pool = m5[(m5.timestamp.dt.hour >= 7) & (m5.timestamp.dt.hour < 19)].index.values
    med_n = int(np.median([len(v) for v in d1.values()]))
    ri = rng.choice(pool, size=min(med_n, len(pool)), replace=False)
    rsig = pd.DataFrame({"timestamp": m5.timestamp.iloc[ri].reset_index(drop=True),
                         "direction": rng.choice([-1, 1], size=len(ri))})
    Rrnd = R6.backtest(m5, rsig, sp5, fall, 1.0, **EXEC)
    out["RANDOM"] = R6.stats(Rrnd)
    Rs["RANDOM"] = Rrnd
    for cell in d1:
        a = Rs[cell][np.isfinite(Rs[cell])]; b = Rrnd[np.isfinite(Rrnd)]
        if len(a) >= 100 and len(b) >= 30:
            p, diff = permutation_diff_p(a, b)
        else:
            p, diff = 1.0, 0.0
        out[cell]["perm_p_vs_random"] = round(float(p), 4)
        P.append(float(p) if out[cell]["n"] >= 100 else 1.0)
    q = bh_fdr_real(P)
    for k, qq in zip(list(d1.keys()), q):
        out[k]["q"] = round(float(qq), 4)
    # D2: base + single filters, contrast vs base
    Rb = R6.backtest(m5, d2["REJ_BASE"], sp5, fall, 1.0, **EXEC)
    Sb = R6.stats(Rb)
    e2b = float(np.nanmean(R6.backtest(m5, d2["REJ_BASE"], sp5, fall, 2.0, **EXEC))) if len(Rb) else None
    Sb["exp_R_2x"] = round(e2b, 4) if e2b is not None and np.isfinite(e2b) else None
    out["REJ_BASE"] = Sb
    Rb = Rb[np.isfinite(Rb)]
    Pf = []
    for cell in [c for c in d2 if c != "REJ_BASE"]:
        r = R6.backtest(m5, d2[cell], sp5, fall, 1.0, **EXEC)
        st = R6.stats(r)
        e2 = float(np.nanmean(R6.backtest(m5, d2[cell], sp5, fall, 2.0, **EXEC))) if len(r) else None
        st["exp_R_2x"] = round(e2, 4) if e2 is not None and np.isfinite(e2) else None
        r = r[np.isfinite(r)]
        if len(r) >= 50 and len(Rb) >= 50:
            p, diff = permutation_diff_p(r, Rb)
        else:
            p, diff = 1.0, 0.0
        st["perm_p_vs_base"] = round(float(p), 4)
        st["diff_vs_base"] = round(float(diff), 4)
        out[cell] = st
        Pf.append(float(p) if st["n"] >= 50 else 1.0)
    qf = bh_fdr_real(Pf)
    for k, qq in zip([c for c in d2 if c != "REJ_BASE"], qf):
        out[k]["q_vs_base"] = round(float(qq), 4)
    return out


def main():
    out = {"prereg": "R6-round3; VWAP/EMA probes + REJ single filters; SL1/TP1/12b",
           "research": {}, "validation": {}, "walkforward": {}, "news": "DATA GAP - no timestamped feed"}
    for split, years, tag in [("research_data", [2020, 2021, 2022], "research"),
                              ("validation_data", [2023], "validation")]:
        m1 = R6.load_m1(split)
        m5 = R6.build_m5(m1)
        m5 = add_anchors(m1, m5)
        sp5 = R6.load_spread_m5(years)
        fall = float(sp5.spread.mean()) if sp5 is not None else 0.35
        out[tag] = evaluate(m5, sp5, fall, None)
        print(tag, "done", flush=True)
    m1all = pd.concat([R6.load_m1("research_data"), R6.load_m1("validation_data")]).sort_values("timestamp")
    yrs = m1all.timestamp.dt.year.values
    for tr, te in [([2020], [2021]), ([2020, 2021], [2022]), ([2020, 2021, 2022], [2023])]:
        sub = m1all[np.isin(yrs, te)].reset_index(drop=True)
        m5t = R6.build_m5(sub)
        m5t = add_anchors(sub, m5t)
        sp = R6.load_spread_m5(te)
        f = float(sp.spread.mean()) if sp is not None else 0.35
        d1 = d1_cells(m5t)
        d2, _ = d2_cells(m5t)
        wf = {}
        for cell, sig in list(d1.items()) + [("REJ_BASE", d2["REJ_BASE"])]:
            r = R6.backtest(m5t, sig, sp, f, 1.0, **EXEC)
            st = R6.stats(r)
            wf[cell] = {"n": st.get("n", 0), "exp_R": st.get("exp_R"), "ci95": st.get("ci95")}
        out["walkforward"][f"{tr}->{te}"] = wf
    print("walkforward done", flush=True)
    with open(ROOT/"reports"/"round3.json", "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)
    log_experiment({"hypothesis": "R6 round3 VWAP/EMA + REJ filters", "dataset": "research 2020-22 -> validation 2023",
                    "results": {"d1": 16, "d2": 14}, "status": "REJECTED"})
    for split in ["research", "validation"]:
        print(f"== {split} D1 ==", flush=True)
        for c, s in out[split].items():
            if c.startswith(("VWAP", "EMA")):
                print(f"{c:22s} n={s.get('n')} exp={s.get('exp_R')} ci={s.get('ci95')} "
                      f"Pret={s.get('P_return_half')} MFE={s.get('MFE_atr')} MAE={s.get('MAE_atr')} "
                      f"2x={s.get('exp_R_2x')} p={s.get('perm_p_vs_random')} q={s.get('q')}", flush=True)
        print(f"== {split} D2 ==", flush=True)
        for c, s in out[split].items():
            if c.startswith("REJ"):
                print(f"{c:14s} n={s.get('n')} exp={s.get('exp_R')} ci={s.get('ci95')} "
                      f"2x={s.get('exp_R_2x')} p_base={s.get('perm_p_vs_base')} q={s.get('q_vs_base')}", flush=True)
    return out


if __name__ == "__main__":
    main()
