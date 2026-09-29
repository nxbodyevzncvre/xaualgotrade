"""TICK-SPREAD VERIFICATION (prereg reports/PREREG_TICK_SPREAD.md).
Order: research characterization (2020-22) -> validation calc (2023). 2024+ never read.
FDR family = preregistered 7 F5 cells: F5_1 UP/DN/NEU + F5_2 UPUP/DNUP/UPDN/DNDN.
Directional net fade exists for 6 cells (NEU has no fade direction); NEU enters the
same BH-FDR family via a return-vector permutation p (no trade direction)."""
import json, sys
import math
from pathlib import Path
import pandas as pd, numpy as np
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import microstructure as MS
from statsx.permutation import permutation_diff_p, bootstrap_mean_ci, bh_fdr_real
from research.registry import log_experiment

AGG = ROOT/"data"/"raw"/"_tickagg"
# 6 directional cells (fade defined) + NEU (return-vector only) = prereg 7-cell family
DIR6 = ["UP", "DN", "UPUP", "DNUP", "UPDN", "DNDN"]
FAMILY7 = ["UP", "DN", "NEU", "UPUP", "DNUP", "UPDN", "DNDN"]
FADE_DIR = {"UP": -1, "DN": 1, "UPUP": -1, "DNUP": -1, "UPDN": 1, "DNDN": 1}


def _finite_float(x, nd=4):
    """JSON-safe rounding: non-finite -> None (B8: no NaN literals in output)."""
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(v):
        return None
    return round(v, nd)

def load_minutes(years):
    frames = []
    for y in years:
        for m in range(1, 13):
            p = AGG/f"min_{y}{m:02d}.csv"
            if not p.exists():
                raise FileNotFoundError(f"missing {p} — run dl_tick for {y}-{m:02d}")
            frames.append(pd.read_csv(p, parse_dates=["timestamp"]))
    df = pd.concat(frames).sort_values("timestamp").drop_duplicates("timestamp").reset_index(drop=True)
    df["timestamp"] = pd.to_datetime(df.timestamp, utc=True)
    wd = df.timestamp.dt.weekday
    return df[(wd < 5)].reset_index(drop=True)  # R5-SESSION-001

def to_m5(minute_df, col="mid_close"):
    g = minute_df.set_index("timestamp")
    o = g[col].resample("5min").first(); h = g[col].resample("5min").max()
    l = g[col].resample("5min").min(); c = g[col].resample("5min").last()
    sp = g["spread_mean"].resample("5min").mean()
    nt = g["n_ticks"].resample("5min").sum()
    m5 = pd.DataFrame({"open": o, "high": h, "low": l, "close": c, "spread": sp, "n_ticks": nt}).dropna().reset_index()
    m5 = MS.add_sessions(m5)
    tr = pd.concat([m5.high-m5.low, (m5.high-m5.close.shift(1)).abs(),
                    (m5.low-m5.close.shift(1)).abs()], axis=1).max(axis=1)
    m5["atr14"] = tr.rolling(14, min_periods=14).mean()
    m5["ret"] = m5.close.pct_change()
    m5["vol_state"] = m5.ret.rolling(240, min_periods=240).std().rolling(2000, min_periods=2000).rank(pct=True)
    m5["vol_state"] = pd.cut(m5.vol_state, [0, .33, .66, 1.0], labels=["LOW", "NORM", "HIGH"])
    d = pd.Series(np.where(m5.ret/m5.atr14*m5.close > 0.02, "UP",
                  np.where(m5.ret/m5.atr14*m5.close < -0.02, "DN", "NEU")), index=m5.index)
    m5["d1"] = d
    return m5

def masks(m5):
    d1, d0 = m5.d1, m5.d1.shift(1)
    return {"UP": d1 == "UP", "DN": d1 == "DN", "NEU": d1 == "NEU",
            "UPUP": (d1 == "UP") & (d0 == "UP"), "DNUP": (d1 == "UP") & (d0 == "DN"),
            "UPDN": (d1 == "DN") & (d0 == "UP"), "DNDN": (d1 == "DN") & (d0 == "DN")}


def build_bid_m5(bid_m1):
    """Bid M5 OHLC + true-range ATR14 (B4: same ATR concept as mid leg, R5 definition).

    bid_m1 columns: timestamp, open, high, low, close (M1 Dukascopy).
    Returns frame with timestamp, bid_close, bid_atr (true-range rolling-14).
    """
    g = bid_m1.set_index("timestamp")
    o = g.open.resample("5min").first(); h = g.high.resample("5min").max()
    l = g.low.resample("5min").min(); c = g.close.resample("5min").last()
    m5 = pd.DataFrame({"bid_close": c, "bh": h, "bl": l,
                       "bo": o}).dropna().reset_index()
    tr = pd.concat([m5.bh - m5.bl, (m5.bh - m5.bid_close.shift(1)).abs(),
                    (m5.bl - m5.bid_close.shift(1)).abs()], axis=1).max(axis=1)
    m5["bid_atr"] = tr.rolling(14, min_periods=14).mean()
    return m5[["timestamp", "bid_close", "bid_atr"]]


def next_ret_diff(close, atr):
    """Next-bar target in ATR units (B3: prereg/R5 diff-over-ATR, NOT pct/ATR).

    target[t] = (close[t+1] - close[t]) / atr[t].
    Causal: state at bar t (built from closes <= t) conditions the move t -> t+1.
    Feature at t can never use return from t as its own target: the target's
    forward difference starts at close[t], the state's backward return ends at
    close[t]; no shared future bar.
    """
    return (close.shift(-1) - close) / atr

def spread_cells(minute_df, m5):
    key = minute_df.timestamp.dt.floor("5min")
    st = m5.set_index("timestamp")
    out = {}
    for s in ["asian", "london", "ny", "off"]:
        for v in ["LOW", "NORM", "HIGH"]:
            for f in ["UP", "DN", "NEU"]:
                lab = st[(st.session == s) & (st.vol_state.astype(str) == v) & (st.d1 == f)].index
                vals = minute_df[minute_df.timestamp.dt.floor("5min").isin(lab)].spread_mean.values
                if len(vals) == 0: continue
                out[f"{s}/{v}/{f}"] = {"n_min": int(len(vals)),
                    "mean": round(float(vals.mean()), 4), "median": round(float(np.median(vals)), 4),
                    "p90": round(float(np.quantile(vals, .9)), 4)}
    return out

def signflip_p(x, B=2000, seed=0):
    rng = np.random.default_rng(seed)
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    if len(x) < 30: return 1.0, float(x.mean()) if len(x) else 0.0
    obs = x.mean(); c = sum(abs((x*rng.choice([-1., 1.], size=len(x))).mean()) >= abs(obs) for _ in range(B))
    return (c+1)/(B+1), obs

def cell_frame(mid_m5, bid_m5):
    """Timestamp-paired mid/bid M5 frame (inner merge; both legs share gaps).

    States (d1) come from the MID leg per prereg; bid leg supplies bid_close/bid_atr.
    Next-bar targets (B1/B3): diff-over-ATR, state at t -> move t->t+1.
    """
    m = mid_m5.merge(bid_m5, on="timestamp", how="inner")
    m["bid_next"] = next_ret_diff(m.bid_close, m.bid_atr)
    m["mid_next"] = next_ret_diff(m.close, m.atr14)
    return m


def research_gross_signs(m5_r):
    """Research-side (2020-22) gross fade-implied sign per directional cell (B5).

    Bid-based next-M5 return in bid-ATR units, conditioned on MID-M5 states
    (same construction as validation gross). Returns {cell: {mean_atr, sign, n}}.
    Firewall: research_data/XAUUSD_M1_duk.csv is 2020-01-01 -> 2022-12-30 only.
    """
    bid_r = pd.read_csv(ROOT/"research_data"/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
    bid_r["timestamp"] = pd.to_datetime(bid_r.timestamp, utc=True)
    bid_r = MS.session_filter(bid_r)
    m = cell_frame(m5_r, build_bid_m5(bid_r))
    mm_r = masks(m)
    signs = {}
    for cell in DIR6:
        mk = mm_r[cell].fillna(False).values
        # B1: state at t (mk) conditions target at t (bid_next[t] = move t->t+1).
        # Drop the terminal row where shift(-1) target is NaN; assert shared convention.
        assert len(mk) == len(m.bid_next.values), "mask/target length mismatch (research)"
        t = m.bid_next.values[:-1]
        k = mk[:-1]
        g = t[k]
        g = g[np.isfinite(g)]
        mg, _, _ = bootstrap_mean_ci(g)
        signs[cell] = {"mean_atr": _finite_float(mg), "n": int(len(g)),
                       "sign": int(np.sign(mg)) if np.isfinite(mg) and mg != 0 else 0}
    return signs


def _ci_excludes_zero(ci):
    lo, hi = ci
    if lo is None or hi is None:
        return False
    return lo > 0 or hi < 0


def _sgn(ci):
    lo, hi = ci
    if lo is None or hi is None:
        return 0
    if lo > 0:
        return 1
    if hi < 0:
        return -1
    return 0


def main():
    out = {"spread_cells_research": {}, "spread_cells_validation": {},
           "research_gross_sign": {}, "gross_bid": {}, "mid_genuine": {},
           "artifact": {}, "net": {}, "decision": None}

    # ---- 1. research-side spread characterization (2020-22) ----
    min_r = load_minutes([2020, 2021, 2022])
    m5_r = to_m5(min_r)
    out["spread_cells_research"] = spread_cells(min_r, m5_r)
    all_r = min_r.spread_mean.values
    out["spread_cells_research"]["__overall__"] = {"n_min": int(len(all_r)),
        "mean": round(float(all_r.mean()), 4), "median": round(float(np.median(all_r)), 4),
        "p90": round(float(np.quantile(all_r, .9)), 4)}
    print("research spread overall:", out["spread_cells_research"]["__overall__"], flush=True)
    # B5: research gross sign reference (computed BEFORE any validation gating)
    out["research_gross_sign"] = research_gross_signs(m5_r)
    print("research gross signs:", out["research_gross_sign"], flush=True)

    # ---- 2. validation (2023): gross bid + mid genuine + artifact + net ----
    min_v = load_minutes([2023])
    m5_mid = to_m5(min_v)
    # bid M5 for 2023 from existing bid file (validation_data = 2023 only, firewall-permitted)
    bid = pd.read_csv(ROOT/"validation_data"/"XAUUSD_M1_duk.csv", parse_dates=["timestamp"])
    bid["timestamp"] = pd.to_datetime(bid.timestamp, utc=True)
    bid = MS.session_filter(bid)
    m5 = cell_frame(m5_mid, build_bid_m5(bid))
    mm = masks(m5)
    out["spread_cells_validation"] = spread_cells(min_v, m5_mid)
    all_v = min_v.spread_mean.values
    out["spread_cells_validation"]["__overall__"] = {"n_min": int(len(all_v)),
        "mean": round(float(all_v.mean()), 4), "median": round(float(np.median(all_v)), 4),
        "p90": round(float(np.quantile(all_v, .9)), 4)}
    print("validation spread overall:", out["spread_cells_validation"]["__overall__"], flush=True)

    P = []
    for cell in FAMILY7:
        mk = mm[cell].fillna(False).values
        # B1: causal next-bar convention — state at t, move t->t+1 — shared by
        # gross, mid, artifact AND net (net loop below uses the same mk[:-1]).
        assert len(mk) == len(m5), "mask/frame length mismatch (validation)"
        gb = m5.bid_next.values[:-1]
        gm = m5.mid_next.values[:-1]
        k = mk[:-1]
        g_raw, m_raw = gb[k], gm[k]
        # B2: single joint finite mask -> timestamp-paired d_i = bid_ret_i - mid_ret_i
        joint = np.isfinite(g_raw) & np.isfinite(m_raw)
        g, m_ = g_raw[joint], m_raw[joint]
        d = g - m_
        mg, glo, ghi = bootstrap_mean_ci(g); mm_, mlo, mhi = bootstrap_mean_ci(m_)
        md, dlo, dhi = bootstrap_mean_ci(d)
        out["gross_bid"][cell] = {"n": int(len(g)), "mean_atr": _finite_float(mg),
                                  "ci95": [_finite_float(glo), _finite_float(ghi)]}
        out["mid_genuine"][cell] = {"n": int(len(m_)), "mean_atr": _finite_float(mm_),
                                    "ci95": [_finite_float(mlo), _finite_float(mhi)]}
        out["artifact"][cell] = {"n": int(len(d)), "mean_atr": _finite_float(md),
                                 "ci95": [_finite_float(dlo), _finite_float(dhi)]}
        if cell in DIR6:
            # net fade: fade UP* -> short(-1); fade DN* -> long(+1)
            direction = FADE_DIR[cell]
            ce = m5.close.values[:-1][k]; cx = m5.close.values[1:][k]
            se = m5.spread.values[:-1][k]; sx = m5.spread.values[1:][k]
            ae = m5.atr14.values[:-1][k]
            ok = np.isfinite(ce) & np.isfinite(cx) & np.isfinite(se) & np.isfinite(sx) & np.isfinite(ae) & (ae > 0)
            net_usd = direction*(cx[ok]-ce[ok])-(se[ok]+sx[ok])/2
            net_atr = net_usd/ae[ok]
            mn, nlo, nhi = bootstrap_mean_ci(net_atr)
            p, obs = signflip_p(net_atr)
            out["net"][cell] = {"n": int(ok.sum()), "mean_usd": _finite_float(net_usd.mean()) if ok.sum() else None,
                                "mean_atr": _finite_float(mn), "ci95": [_finite_float(nlo), _finite_float(nhi)],
                                "p": round(float(p), 4)}
            P.append(float(p) if ok.sum() >= 30 else 1.0)
        else:
            # NEU: no fade direction (prereg); enters the SAME 7-cell BH family via a
            # return-vector permutation p (mid next-ret NEU vs rest). Uses the
            # prereg-specified permutation_diff_p (B=2000, seed 0).
            x1 = m5.mid_next.values[:-1][k]
            x0 = m5.mid_next.values[:-1][~mk[:-1]]
            p_neu, _ = permutation_diff_p(x1, x0)
            out["net"][cell] = {"n": None, "mean_usd": None, "mean_atr": None,
                                "ci95": [None, None], "p": round(float(p_neu), 4),
                                "note": "no fade direction; return-vector permutation p only"}
            P.append(float(p_neu))

    q = bh_fdr_real(P)
    for k, qq in zip(FAMILY7, q):
        out["net"][k]["q"] = round(float(qq), 4)


    # D1/D2 literally per prereg (B5): D2 = net CI excludes 0 (either side) AND q<0.10
    # AND same sign as research gross. A significantly NEGATIVE net is a phenomenon
    # candidate too — it must NOT be classified as a positive edge, only recorded with
    # its sign; D1 covers the no-significance case only.
    ok_cells, sign_mismatch = [], []
    for k in DIR6:
        ci = out["net"][k]["ci95"]
        if not _ci_excludes_zero(ci) or out["net"][k]["q"] >= 0.10:
            continue
        if _sgn(ci) == out["research_gross_sign"][k]["sign"] and out["research_gross_sign"][k]["sign"] != 0:
            ok_cells.append(k)
        else:
            sign_mismatch.append(k)
    if not ok_cells:
        if sign_mismatch:
            out["decision"] = ("D1: no cell meets the full D2 conjunction. Significant but "
                               f"sign-mismatched vs research gross: {sign_mismatch} (NOT candidates, "
                               "sign does not replicate). STOP stands.")
        else:
            out["decision"] = "D1: all net CIs include 0 or q>=0.10 -> F5 = quote artifact or sub-cost noise. STOP stands."
    else:
        out["decision"] = (f"D2: candidate cells {ok_cells} (net CI excludes 0, q<0.10, sign matches "
                           "research gross; phenomenon, NOT strategy). No 2024+ inspection.")
    status = "PROMISING" if ok_cells else "REJECTED"  # B7: branch, no hardcoded status
    log_experiment({"hypothesis": "tick-spread verification", "dataset": "2023 validation tick; 2020-22 research",
                    "results": {"qmin": float(min(q)), "decision": out["decision"],
                                "family": FAMILY7}, "status": status})
    with open(ROOT/"reports"/"tickspread.json", "w") as f:
        json.dump(out, f, indent=2, allow_nan=False)  # B8: invalid NaN raises instead of silent corrupt JSON
    print(json.dumps({"net": out["net"], "research_gross_sign": out["research_gross_sign"],
                      "decision": out["decision"]}, indent=2))
    return out


if __name__ == "__main__":
    main()

