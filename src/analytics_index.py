"""Write machine-readable index of outputs/ for dashboard + LLM grounding."""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def build_index(output_dir: Path) -> dict:
    out: dict = {"root": str(output_dir), "datasets": []}
    if not output_dir.exists():
        return out
    for p in sorted(output_dir.rglob("*.csv")):
        rel = p.relative_to(output_dir).as_posix()
        try:
            df = pd.read_csv(p, nrows=0)
            cols = [{"name": c, "dtype": str(df[c].dtype)} for c in df.columns]
            with open(p, encoding="utf-8", errors="replace") as fh:
                nrow = max(0, sum(1 for _ in fh) - 1)
        except Exception as e:
            cols = []
            nrow = -1
            err = str(e)
        else:
            err = None
        out["datasets"].append(
            {
                "rel": rel,
                "rows": nrow,
                "columns": cols,
                "error": err,
            }
        )
    return out


def write_index(output_dir: Path, dest: Path | None = None) -> Path:
    dest = dest or (output_dir / "analytics_index.json")
    idx = build_index(output_dir)
    dest.write_text(json.dumps(idx, indent=2), encoding="utf-8")
    return dest
