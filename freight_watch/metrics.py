"""Weekly cost-per-tonne-km per route plus the two required baselines."""
import numpy as np
import pandas as pd

from . import config


def load_shipments(path=config.SHIPMENTS_CSV) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["shipment_date"])
    df["route"] = df["origin"] + "-" + df["destination"]
    # Weeks run Monday-Sunday; week_of is that week's Monday.
    df["week_of"] = df["shipment_date"] - pd.to_timedelta(df["shipment_date"].dt.weekday, unit="D")
    df["tonne_km"] = df["quantity_tonnes"] * df["distance_km"]
    return df


def weekly_costs(df: pd.DataFrame) -> pd.DataFrame:
    """One row per (route, route_type, week): total cost / total tonne-km."""
    w = (df.groupby(["route", "route_type", "week_of"], as_index=False)
           .agg(cost=("freight_cost_inr", "sum"), tonne_km=("tonne_km", "sum")))
    w["cpt"] = w["cost"] / w["tonne_km"]
    return w.sort_values(["route", "week_of"]).reset_index(drop=True)


def add_baselines(w: pd.DataFrame) -> pd.DataFrame:
    """Adds own-history and peer baselines exactly as defined in the brief."""
    w = w.copy()
    hist_avg, hist_sd, n_hist = [], [], []
    for _, g in w.groupby("route", sort=False):
        v = g["cpt"].to_numpy()
        for i in range(len(v)):
            h = v[max(0, i - config.HISTORY_WINDOW_WEEKS):i]   # strictly before week i
            n_hist.append(len(h))
            hist_avg.append(h.mean() if len(h) else np.nan)
            hist_sd.append(h.std(ddof=1) if len(h) >= config.MIN_HISTORY_FOR_ZSCORE else np.nan)
    w["hist_avg"], w["hist_sd"], w["n_hist"] = hist_avg, hist_sd, n_hist

    # Peers: mean cpt of the *other* routes of the same route_type in the same week.
    grp = w.groupby(["route_type", "week_of"])["cpt"]
    s, c = grp.transform("sum"), grp.transform("count")
    w["peer_avg"] = np.where(c > 1, (s - w["cpt"]) / (c - 1).replace(0, np.nan), np.nan)

    w["vs_own"] = w["cpt"] / w["hist_avg"] - 1
    w["vs_peer"] = w["cpt"] / w["peer_avg"] - 1
    w["z"] = (w["cpt"] - w["hist_avg"]) / w["hist_sd"]
    return w
