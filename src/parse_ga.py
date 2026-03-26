"""Parse GA4 'Reports snapshot' CSV (comment-prefixed sections) into DataFrames."""
from __future__ import annotations

import csv
import io
from pathlib import Path

import pandas as pd


def parse_ga_snapshot(path: Path) -> dict[str, pd.DataFrame]:
    """
    Split snapshot file into labeled tables. Each table: non-comment header row
    followed by data rows until blank line or next comment block.
    """
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = text.splitlines()
    sections: dict[str, pd.DataFrame] = {}
    i = 0
    section_idx = 0

    while i < len(lines):
        line = lines[i]
        if line.strip().startswith("#"):
            i += 1
            continue
        if not line.strip():
            i += 1
            continue
        if "," not in line:
            i += 1
            continue

        header = line.strip()
        block_lines = [header]
        i += 1
        while i < len(lines):
            ln = lines[i]
            if not ln.strip():
                break
            if ln.strip().startswith("#"):
                break
            block_lines.append(ln.strip())
            i += 1

        buf = io.StringIO("\n".join(block_lines))
        try:
            df = pd.read_csv(buf)
        except Exception:
            i += 1
            continue

        if df.empty or len(df.columns) < 1:
            continue

        key = f"section_{section_idx:03d}_{df.columns[0][:40]}"
        sections[key] = df
        section_idx += 1

    return sections


def save_ga_tables(sections: dict[str, pd.DataFrame], out_dir: Path) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, df in sections.items():
        safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in name)[:120]
        df.to_csv(out_dir / f"{safe}.csv", index=False)


def extract_daily_series(
    sections: dict[str, pd.DataFrame], col_substr: str = "Active users"
) -> pd.DataFrame | None:
    """Find first two-column daily series whose first column looks like Nth day."""
    for df in sections.values():
        if len(df.columns) < 2:
            continue
        c0, c1 = df.columns[0], df.columns[1]
        if col_substr.lower() in str(c1).lower():
            try:
                day = df[c0].astype(str).str.strip().str.lstrip("0")
                day = pd.to_numeric(day.replace("", "0"), errors="coerce")
                if day.notna().sum() > 10:
                    out = df[[c0, c1]].copy()
                    out.columns = ["nth_day", "value"]
                    return out
            except Exception:
                continue
    return None
