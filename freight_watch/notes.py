"""Context notes: parsing of scope/time window/polarity, and TF-IDF retrieval.

Retrieval finds *candidate* notes; deterministic gates then decide whether a note may
justify a rise. A note justifies only if ALL hold:
  1. scope  - applies_to is the route or 'All Routes'
  2. window - the note's effect window overlaps the week
  3. effect - the note says costs went UP (not 'no disruption', 'normal', 'not affected')
"""
import re
from dataclasses import dataclass
from datetime import date, timedelta

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from . import config

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}

# Cost-raising cues vs. neutralising cues (checked on lowercase text).
RAISE = re.compile(r"\b(higher|surcharge|pushing up|rose|increase|raised|detour|costlier)\b")
NEUTRAL = re.compile(
    r"not significantly affected|costs were not|no major disruptions|no significant disruptions|"
    r"remained (stable|normal)|returned to normal|without a rate change|absorbed|"
    r"not part of this dataset|improved road|minor delays")
LEVEL_SHIFT = re.compile(r"\bstarting this week\b|\bfrom this week\b")
RANGE = re.compile(r"from ([A-Z][a-z]{2}) (\d{1,2}) to ([A-Z][a-z]{2}) (\d{1,2})")


@dataclass(frozen=True)
class Note:
    note_id: str
    date: date
    applies_to: str
    text: str
    raises_cost: bool
    win_start: date
    win_end: date


def _monday(d: date) -> date:
    return d - timedelta(days=d.weekday())


def _parse_window(nid_date: date, text: str):
    m = RANGE.search(text)
    if m:
        s = date(nid_date.year, MONTHS[m.group(1).lower()], int(m.group(2)))
        e = date(nid_date.year, MONTHS[m.group(3).lower()], int(m.group(4)))
        if e < s:
            e = e.replace(year=e.year + 1)
        return s, e
    start = _monday(nid_date)
    if LEVEL_SHIFT.search(text.lower()):
        return start, start + timedelta(weeks=config.LEVEL_SHIFT_EFFECT_WEEKS) - timedelta(days=1)
    return start, start + timedelta(days=6)          # single-week event


def load_notes(path=config.NOTES_CSV) -> list[Note]:
    out = []
    for r in pd.read_csv(path).itertuples():
        d = pd.Timestamp(r.date).date()
        low = r.note.lower()
        raises = bool(RAISE.search(low)) and not NEUTRAL.search(low)
        s, e = _parse_window(d, r.note)
        out.append(Note(r.note_id, d, r.applies_to.strip(), r.note.strip(), raises, s, e))
    return out


class NoteIndex:
    """TF-IDF index over notes (in-memory, deterministic, no network)."""

    def __init__(self, notes: list[Note]):
        self.notes = notes
        self.vec = TfidfVectorizer(ngram_range=(1, 2), stop_words="english")
        self.mat = self.vec.fit_transform([f"{n.applies_to}. {n.text}" for n in notes])

    def retrieve(self, route: str, k: int = config.TOP_K_NOTES) -> list[Note]:
        q = self.vec.transform([f"{route.replace('-', ' ')} {route} cost rise surcharge disruption"])
        sims = cosine_similarity(q, self.mat).ravel()
        # stable tie-break on note_id for reproducibility
        order = sorted(range(len(self.notes)), key=lambda i: (-round(sims[i], 12), self.notes[i].note_id))
        return [self.notes[i] for i in order[:k]]


def in_scope(n: Note, route: str) -> bool:
    return n.applies_to.lower() == "all routes" or n.applies_to == route


def overlaps_week(n: Note, week_of: date) -> bool:
    return n.win_start <= week_of + timedelta(days=6) and n.win_end >= week_of


def find_justifying_note(index: NoteIndex, route: str, week_of: date):
    """Return the justifying Note, or None. Route-specific notes win over All-Routes."""
    scoped = [n for n in index.notes if in_scope(n, route)]
    ok = [n for n in scoped if n.raises_cost and overlaps_week(n, week_of)]
    ok.sort(key=lambda n: (n.applies_to == "All Routes", n.note_id))
    return ok[0] if ok else None


def closest_in_scope_note(index: NoteIndex, route: str, week_of: date):
    """Nearest-in-time in-scope note, for explaining *why* an unexplained row has no cause."""
    scoped = [n for n in index.notes if in_scope(n, route)]
    scoped = [n for n in scoped if abs((n.date - week_of).days) <= config.CLOSEST_NOTE_MAX_DAYS]
    if not scoped:
        return None
    return sorted(scoped, key=lambda n: (abs((n.date - week_of).days), n.note_id))[0]
