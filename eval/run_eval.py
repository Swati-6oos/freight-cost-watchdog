"""Eval harness. Scores the pipeline against a hand-labelled set (eval/labels.csv) over
ALL route-weeks, so both missed anomalies and false alarms count.

Also checks (a) numbers against the 3 numeric rows in the provided sample file and
(b) hallucination guardrails: every justified row cites a note that is in-scope,
in-window and cost-raising."""
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from freight_watch import config, pipeline
from freight_watch.notes import in_scope, load_notes, overlaps_week


def main() -> int:
    out = pipeline.run()
    labels = pd.read_csv(ROOT / "eval" / "labels.csv", dtype=str).fillna("")
    key = lambda df: set(zip(df.route, df.week_of))
    pred, gold = key(out), key(labels)
    tp = len(pred & gold)
    prec, rec = tp / max(len(pred), 1), tp / max(len(gold), 1)
    print(f"[detection]  predicted={len(pred)} gold={len(gold)} precision={prec:.2f} recall={rec:.2f}")
    print(f"             false alarms: {sorted(pred - gold)}  missed: {sorted(gold - pred)}")

    m = labels.merge(out, on=["route", "week_of"], how="inner")
    verdict_ok = (m.expected_flagged == m.flagged)
    note_ok = (m.expected_note == m.matched_note_id.fillna("").astype(str))
    print(f"[verdict]    {verdict_ok.sum()}/{len(m)} correct   [cited note] {note_ok.sum()}/{len(m)} correct")

    # Numbers vs the provided sample file (first three rows are real values)
    # The sample's last row has an unquoted comma in `reason`, so split on the first 7 commas.
    lines = (config.ROOT / "data" / "sample_output_format_v2.csv").read_text().splitlines()
    cols = lines[0].split(",")
    sample = pd.DataFrame([ln.split(",", 7) for ln in lines[1:]], columns=cols)
    s = sample.merge(out, on=["route", "week_of"], suffixes=("_s", "_o"))
    num_ok = (s.cost_per_tonne_km_s == s.cost_per_tonne_km_o).sum()
    own_ok = (s.vs_own_history_s == s.vs_own_history_o).sum()
    peer_ok = (s.vs_similar_routes_s == s.vs_similar_routes_o).sum()
    print(f"[sample nums] matched rows={len(s)}  cost ok={num_ok}  own% ok={own_ok}  peer% ok={peer_ok}")

    # Guardrail: every justified row's note must be in scope, in window, cost-raising.
    notes = {n.note_id: n for n in load_notes()}
    bad = []
    for r in out[out.flagged == "No (justified)"].itertuples():
        n = notes.get(r.matched_note_id)
        wk = date.fromisoformat(r.week_of)
        if not (n and in_scope(n, r.route) and overlaps_week(n, wk) and n.raises_cost):
            bad.append((r.route, r.week_of, r.matched_note_id))
    print(f"[guardrail]  invalid justified citations: {bad or 'none'}")
    print(f"[guardrail]  unexplained rows with a note id: "
          f"{int(((out.flagged == 'Yes') & (out.matched_note_id.fillna('') != '')).sum())}")

    ok = (prec == 1 and rec == 1 and verdict_ok.all() and note_ok.all() and not bad)
    print("RESULT:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
