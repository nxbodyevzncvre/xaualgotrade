"""Chronological split + walk-forward. Discovery code must never read final slice."""
import pandas as pd

def chrono_split(df: pd.DataFrame, r=0.7, v=0.15):
    n = len(df)
    i1, i2 = int(n*r), int(n*(r+v))
    return df.iloc[:i1].reset_index(drop=True), df.iloc[i1:i2].reset_index(drop=True), df.iloc[i2:].reset_index(drop=True)

def walkforward_windows(df: pd.DataFrame, n_windows=3):
    n = len(df)
    wins = []
    for w in range(n_windows):
        cut = int(n*(0.5 + 0.15*w))
        test_end = int(n*(0.65 + 0.15*w)) if w < n_windows-1 else n
        wins.append((df.iloc[:cut].reset_index(drop=True), df.iloc[cut:test_end].reset_index(drop=True)))
    return wins
