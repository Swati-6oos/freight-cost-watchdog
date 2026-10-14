"""All tunable parameters in one place (nothing here is random)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SHIPMENTS_CSV = ROOT / "data" / "shipment_records.csv"
NOTES_CSV = ROOT / "data" / "context_notes.csv"
OUTPUT_CSV = ROOT / "outputs" / "output.csv"

# Baselines (fixed by the brief)
HISTORY_WINDOW_WEEKS = 8      # trailing weeks, strictly before the current week
MIN_HISTORY_FOR_ZSCORE = 3    # need >=3 prior weeks to estimate volatility

# Anomaly rule: a route-week is a candidate when cost is rising vs own history by at
# least MIN_RISE_VS_OWN AND it is out of the ordinary by at least one of:
#   (a) z-score vs own trailing window >= Z_THRESHOLD   (unusual vs own history)
#   (b) premium over same-type peers   >= PEER_PREMIUM  (unusual vs similar routes)
MIN_RISE_VS_OWN = 0.08
Z_THRESHOLD = 3.0
PEER_PREMIUM = 0.15

# A level-shift note (e.g. a diesel hike) can only explain a rise relative to the
# trailing baseline while that baseline still contains pre-shift weeks.
LEVEL_SHIFT_EFFECT_WEEKS = HISTORY_WINDOW_WEEKS

# Retrieval
TOP_K_NOTES = 3
# For unexplained rows, mention the closest in-scope note only if within this many days.
CLOSEST_NOTE_MAX_DAYS = 90
