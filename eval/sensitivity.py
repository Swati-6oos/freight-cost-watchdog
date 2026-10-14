"""How stable is the candidate set when thresholds move? (prints candidate counts)"""
import sys
from itertools import product
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from freight_watch import config, pipeline

w = pipeline.build_weekly()
print("rise  z   peer  -> candidates")
for rise, z, peer in product([0.06, 0.08, 0.10], [2.5, 3.0, 4.0], [0.10, 0.15, 0.20]):
    n = ((w.vs_own >= rise) & ((w.z >= z) | (w.vs_peer >= peer))).sum()
    mark = "  <- chosen" if (rise, z, peer) == (config.MIN_RISE_VS_OWN, config.Z_THRESHOLD, config.PEER_PREMIUM) else ""
    print(f"{rise:.2f} {z:.1f} {peer:.2f} -> {n}{mark}")
