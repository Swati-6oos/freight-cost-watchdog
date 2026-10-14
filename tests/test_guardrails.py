"""Unit tests for the anti-hallucination gates (run: python -m unittest discover tests)."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from freight_watch.notes import NoteIndex, find_justifying_note, load_notes


class Guardrails(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.idx = NoteIndex(load_notes())

    def cite(self, route, wk):
        n = find_justifying_note(self.idx, route, date.fromisoformat(wk))
        return n.note_id if n else None

    def test_correct_matches(self):
        self.assertEqual(self.cite("Ahmedabad-Mumbai", "2025-01-20"), "N002")
        self.assertEqual(self.cite("Chennai-Bangalore", "2025-03-03"), "N001")
        self.assertEqual(self.cite("Delhi-Jaipur", "2025-05-12"), "N003")  # all-routes diesel

    def test_wrong_route_rejected(self):
        self.assertIsNone(self.cite("Mumbai-Pune", "2025-01-20"))          # N002 is Ahmedabad only

    def test_wrong_window_rejected(self):
        self.assertIsNone(self.cite("Ahmedabad-Mumbai", "2025-01-27"))     # week after festival
        self.assertIsNone(self.cite("Chennai-Bangalore", "2025-03-10"))    # after flood
        self.assertIsNone(self.cite("Mumbai-Pune", "2025-11-17"))          # diesel effect expired

    def test_no_effect_notes_never_justify(self):
        for nid in ["N004", "N005", "N006", "N007", "N008", "N009", "N010"]:
            n = next(x for x in self.idx.notes if x.note_id == nid)
            self.assertFalse(n.raises_cost, nid)

    def test_before_diesel_not_justified(self):
        self.assertIsNone(self.cite("Mumbai-Delhi", "2025-04-28"))


if __name__ == "__main__":
    unittest.main()
