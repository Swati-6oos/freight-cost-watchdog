"""End-to-end run: shipments + notes -> output CSV matching the required format."""
import pandas as pd

from . import config
from .explain import justified_reason, unexplained_reason
from .flagging import find_candidates
from .metrics import add_baselines, load_shipments, weekly_costs
from .notes import NoteIndex, closest_in_scope_note, find_justifying_note, load_notes

COLUMNS = ["route", "week_of", "cost_per_tonne_km", "vs_own_history", "vs_similar_routes",
           "flagged", "matched_note_id", "reason"]


def _pct(x: float) -> str:
    return f"{x * 100:+.1f}%"


def build_weekly() -> pd.DataFrame:
    return add_baselines(weekly_costs(load_shipments()))


def run() -> pd.DataFrame:
    weekly = build_weekly()
    index = NoteIndex(load_notes())
    rows = []
    for r in find_candidates(weekly).itertuples():
        wk = r.week_of.date()
        note = find_justifying_note(index, r.route, wk)
        if note:
            flagged, nid, reason = "No (justified)", note.note_id, justified_reason(note, r.vs_own, wk)
        else:
            flagged, nid = "Yes", ""
            reason = unexplained_reason(closest_in_scope_note(index, r.route, wk), wk)
        rows.append({
            "route": r.route, "week_of": wk.isoformat(),
            "cost_per_tonne_km": f"{r.cpt:.2f}",
            "vs_own_history": f"{_pct(r.vs_own)} vs this route's past average",
            "vs_similar_routes": ("n/a" if pd.isna(r.vs_peer)
                                  else f"{_pct(r.vs_peer)} vs similar-length routes this week"),
            "flagged": flagged, "matched_note_id": nid, "reason": reason})
    out = pd.DataFrame(rows, columns=COLUMNS).sort_values(["week_of", "route"]).reset_index(drop=True)
    return out


def main(path=config.OUTPUT_CSV):
    out = run()
    path.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(path, index=False, lineterminator="\n")
    print(f"Wrote {len(out)} rows to {path}")
    print(out[["route", "week_of", "flagged", "matched_note_id"]].to_string(index=False))


if __name__ == "__main__":
    main()
