"""Candidate detection: cost is rising AND unusual vs own history or vs peers."""
import pandas as pd

from . import config


def find_candidates(w: pd.DataFrame) -> pd.DataFrame:
    rising = w["vs_own"] >= config.MIN_RISE_VS_OWN
    unusual_own = w["z"] >= config.Z_THRESHOLD
    unusual_peer = w["vs_peer"] >= config.PEER_PREMIUM
    return w[rising & (unusual_own | unusual_peer)].copy()
