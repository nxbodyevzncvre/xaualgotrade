"""Experiment registry: append-only JSONL. Never delete failures."""
import json, os, time
from pathlib import Path

REG_PATH = Path(__file__).resolve().parents[1] / "research" / "experiments" / "registry.jsonl"

def log_experiment(rec: dict) -> str:
    REG_PATH.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    if REG_PATH.exists():
        with open(REG_PATH) as f:
            for _ in f:
                n += 1
    exp_id = rec.get("experiment_id") or f"EXP-{n+1:06d}"
    rec = {"experiment_id": exp_id, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **rec}
    with open(REG_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")
    return exp_id

def load_registry():
    if not REG_PATH.exists():
        return []
    out = []
    with open(REG_PATH) as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out
