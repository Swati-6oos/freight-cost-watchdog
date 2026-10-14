"""Template-based, note-grounded explanations (no LLM -> no hallucination, 0 tokens)."""
from .notes import Note, overlaps_week


def _short(text: str, limit: int = 160) -> str:
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def justified_reason(n: Note, w_pct: float, week_of) -> str:
    base = (f"Matches note {n.note_id} dated {n.date.isoformat()} ({n.applies_to}): "
            f"{_short(n.text, 200)} The note's window ({n.win_start} to {n.win_end}) covers "
            f"the week of {week_of}, so the cost rise has a documented explanation.")
    if "5-7%" in n.text and w_pct > 0.07:
        base += (f" Caution: the note cites roughly 5-7%, while this route is up "
                 f"{w_pct * 100:.1f}% vs its own history, so the note may explain only part of it.")
    return base


def unexplained_reason(close: Note | None, week_of) -> str:
    if close is None:
        return ("No matching note found for this route or date range. "
                "Cost rise looks unexplained and worth a human review.")
    why = []
    if not close.raises_cost:
        why.append("it does not describe a reason for a cost rise on this route")
    if not overlaps_week(close, week_of):
        why.append(f"its effect window ({close.win_start} to {close.win_end}) does not cover "
                   f"the week of {week_of}")
    return (f"The closest note ({close.note_id}, {close.date.isoformat()}) says: "
            f"\"{_short(close.text)}\" -- {' and '.join(why)}. "
            "No genuine justification found; flagged for review.")
