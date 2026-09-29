"""Section-30 visual proof: random sampled swing trades (win + loss), not hand-picked."""
import pandas as pd, numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from features import swings as SW, fibonacci as FIB, volatility as V
df = pd.read_csv(ROOT/"research_data"/"XAUUSD_H1.csv", parse_dates=["timestamp"])
df = V.add_volatility(df)
sw = SW.fractal_swings(df, 2)
pairs = FIB.pairs_to_retracements(sw).head(400)
rng = np.random.default_rng(42)
sample = pairs.iloc[rng.choice(len(pairs), size=4, replace=False)]
fig, axes = plt.subplots(2, 2, figsize=(12, 8))
for ax, (_, p) in zip(axes.flat, sample.iterrows()):
    c0 = int(p.confirm_idx)
    seg = df.iloc[max(0, c0-30):c0+25].reset_index(drop=True)
    ax.plot(seg.close.values, lw=1)
    ax.axhline(p.lo, ls="--", lw=1); ax.axhline(p.hi, ls="--", lw=1)
    lp = FIB.level_price(p.lo, p.hi, 0.618, p.direction)
    ax.axhline(lp, lw=1)
    ax.set_title(f"pair {p.pair} {p.direction} 61.8={lp:.1f} confirm={c0}")
    ax.axvline(30 if c0 >= 30 else c0, color="k", lw=1)
fig.suptitle("Random retracement examples (illustrative only — aggregate stats are the evidence)")
fig.tight_layout()
fig.savefig(ROOT/"reports"/"fib_examples_random.png", dpi=100)
print("saved fib_examples_random.png")
