"""Grounding context for the local LLM: only REPORT + outputs summaries."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "outputs"
DOCS = ROOT / "docs"


def build_llm_context(max_chars: int = 24000) -> str:
    parts: list[str] = []

    ms = DOCS / "METHODS_STATUS.md"
    if ms.exists():
        parts.append("=== METHODS STATUS (authoritative scope) ===\n")
        parts.append(ms.read_text(encoding="utf-8", errors="replace")[:6000])

    rp = OUTPUT / "REPORT.md"
    if rp.exists():
        parts.append("\n=== LATEST RUN REPORT ===\n")
        parts.append(rp.read_text(encoding="utf-8", errors="replace")[:8000])

    ix = OUTPUT / "analytics_index.json"
    if ix.exists():
        parts.append("\n=== DATASET INDEX ===\n")
        parts.append(ix.read_text(encoding="utf-8", errors="replace")[:4000])

    # Sample rows from key CSVs (bounded)
    csv_paths = sorted(OUTPUT.rglob("*.csv"))[:25]
    for p in csv_paths:
        if p.name == "analytics_index.json":
            continue
        rel = p.relative_to(OUTPUT).as_posix()
        try:
            df = pd.read_csv(p, nrows=12, low_memory=False)
            blob = df.to_csv(index=False)
            parts.append(f"\n=== SAMPLE: {rel} (first rows) ===\n{blob[:2500]}\n")
        except Exception as e:
            parts.append(f"\n=== {rel} (unreadable: {e}) ===\n")

    text = "\n".join(parts)
    if len(text) > max_chars:
        text = text[: max_chars - 80] + "\n\n[TRUNCATED — context capped for safety]"
    return text


def system_prompt() -> str:
    return """You are a data analysis assistant for FireFly Farms commerce analytics.

RULES (non-negotiable):
- Answer ONLY using the CONTEXT block provided in this conversation. It is built from files under outputs/ and docs/METHODS_STATUS.md.
- If the context does not contain a number, method result, or definition, say clearly that it is not in the current export and do not invent it.
- Prefer citing file names (e.g. association_rules_filtered.csv) when referring to tables.
- Your scope is: interpreting the analytics outputs, explaining metrics (support, confidence, lift, topics, etc.), and suggesting which CSV to open for a business question.
- Do NOT give medical, legal, or personal advice. Do NOT claim to access live systems, the internet, or data outside CONTEXT.
- If asked about the "eleven methods", summarize using METHODS_STATUS in context only.

Tone: concise, professional, actionable for a retail/food brand stakeholder."""


def ollama_chat(messages: list[dict], model: str | None = None) -> tuple[str, str | None]:
    """Returns (assistant_text, error). Uses OLLAMA_HOST (default http://127.0.0.1:11434)."""
    import urllib.error
    import urllib.request

    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = model or os.environ.get("OLLAMA_MODEL", "llama3.2")
    url = f"{host}/api/chat"
    body = json.dumps(
        {"model": model, "messages": messages, "stream": False}
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        msg = data.get("message") or {}
        return (msg.get("content") or str(data), None)
    except urllib.error.URLError as e:
        return ("", str(e))
    except Exception as e:
        return ("", str(e))
