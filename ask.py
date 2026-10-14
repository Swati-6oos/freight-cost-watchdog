"""Stretch goal: ask plain-English questions about the findings.
   python ask.py "why did Chennai-Bangalore get pricier in March?"
Answers are built ONLY from outputs/output.csv (this assistant's own results); no LLM."""
import re
import sys

import pandas as pd

from freight_watch import config, pipeline

MONTHS = ["january", "february", "march", "april", "may", "june", "july",
          "august", "september", "october", "november", "december"]


def answer(q: str, df: pd.DataFrame) -> str:
    ql = q.lower()
    routes = sorted(set(df.route))
    hits = [r for r in routes if any(part.lower() in ql for part in r.split("-"))]
    sel = df[df.route.isin(hits)] if hits else df
    month = next((i for i, m in enumerate(MONTHS, 1) if m in ql or m[:3] + " " in ql + " "), None)
    if month:
        sel = sel[pd.to_datetime(sel.week_of).dt.month == month]
    year = re.search(r"\b(2024|2025)\b", ql)
    if year:
        sel = sel[sel.week_of.str.startswith(year.group(1))]
    if "unexplained" in ql or "flagged" in ql or "review" in ql:
        sel = sel[sel.flagged == "Yes"]
    if sel.empty:
        return ("I found no flagged or justified cost rises matching that question in my results. "
                "That means nothing unusual crossed my thresholds, not that costs were flat.")
    lines = [f"- {r.route}, week of {r.week_of}: {r.cost_per_tonne_km} INR/t-km "
             f"({r.vs_own_history.split(' vs')[0]} vs own history, "
             f"{r.vs_similar_routes.split(' vs')[0]} vs peers). "
             f"Verdict: {r.flagged}"
             f"{' [' + r.matched_note_id + ']' if isinstance(r.matched_note_id, str) and r.matched_note_id else ''}. "
             f"{r.reason}" for r in sel.itertuples()]
    return "\n".join(lines)


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "Which routes are unexplained?"
    df = pd.read_csv(config.OUTPUT_CSV, dtype=str).fillna("") if config.OUTPUT_CSV.exists() else pipeline.run()
    print(answer(q, df))
