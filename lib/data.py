"""Loading and shaping the fleet data.

This demo reads CSV committed alongside the app. Swapping in a real source means
changing only load_all(): everything downstream works off the same four frames.
"""
from pathlib import Path

import pandas as pd
import streamlit as st

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VEHICLE_BOOLS = [
    "rm_cover", "telematics", "cctv", "trailer_tracker", "insurance_database",
    "dart_charge_registered", "congestion_zone_registered", "merseyflow_registered",
    "three_seater",
]
VEHICLE_DATES = [
    "hire_lease_start_date", "inspection_due_date", "mot_due_date", "loler_due_date",
    "service_due_date", "tacho_due_date", "date_added", "date_removed",
]
VOR_BOOLS = ["covered_under_rm", "reported_to_supplier"]
VOR_DATES = ["vor_date", "expected_return_date", "original_expected_return_date", "actual_return_date"]

COMPLIANCE_CHECKS = [
    ("MOT", "mot_due_date"),
    ("Inspection", "inspection_due_date"),
    ("LOLER", "loler_due_date"),
    ("Service", "service_due_date"),
    ("Tacho", "tacho_due_date"),
]

UTILISED_STATUSES = {"Out for Delivery", "RELOAD PT 2"}


def _read(name, date_cols=(), bool_cols=()):
    df = pd.read_csv(DATA_DIR / f"{name}.csv")
    for c in date_cols:
        if c in df.columns:
            df[c] = pd.to_datetime(df[c], errors="coerce")
    for c in bool_cols:
        if c in df.columns:
            df[c] = df[c].fillna(0).astype(int).astype(bool)
    return df


@st.cache_data(show_spinner=False)
def load_all():
    vehicles = _read("vehicles", VEHICLE_DATES, VEHICLE_BOOLS)
    vor = _read("vor_records", VOR_DATES, VOR_BOOLS)
    transport = _read("transport_logs", ["log_date"], ["utilised"])
    depots = _read("depots", bool_cols=["active"])

    today = pd.Timestamp(pd.Timestamp.today().date())

    # The one rule for days off road, applied once here so no page can disagree:
    # open record   -> today minus vor_date
    # closed record -> actual_return_date minus vor_date
    end = vor["actual_return_date"].where(vor["status"] == "Returned", today)
    vor["days_off_road"] = (end - vor["vor_date"]).dt.days
    vor["days_vs_eta"] = (today - vor["expected_return_date"]).dt.days
    vor["overdue"] = (vor["status"] == "Open") & (vor["expected_return_date"] < today)
    vor["month"] = vor["vor_date"].dt.to_period("M").dt.to_timestamp()
    vor["late_vs_promise"] = (
        (vor["status"] == "Returned")
        & (vor["actual_return_date"] > vor["original_expected_return_date"])
    )

    return {
        "vehicles": vehicles,
        "vor": vor,
        "transport": transport,
        "depots": depots,
        "today": today,
    }


def apply_depot(df, depot):
    """Apply the global depot filter to any frame carrying a depot column."""
    if depot == "All depots" or "depot" not in df.columns:
        return df
    return df[df["depot"] == depot]


def active_fleet(vehicles):
    return vehicles[vehicles["status"] != "Removed"]


def open_vor(vor):
    return vor[vor["status"] == "Open"]


def closed_vor(vor):
    return vor[vor["status"] == "Returned"]


def compliance_frame(vehicles, today):
    """One row per vehicle per applicable check, with days until it is due."""
    rows = []
    for label, col in COMPLIANCE_CHECKS:
        sub = vehicles[vehicles[col].notna()][["reg", "depot", "vehicle_type", col]].copy()
        sub["check"] = label
        sub["due"] = sub[col]
        sub["days_until"] = (sub["due"] - today).dt.days
        rows.append(sub[["reg", "depot", "vehicle_type", "check", "due", "days_until"]])
    if not rows:
        return pd.DataFrame(columns=["reg", "depot", "vehicle_type", "check", "due", "days_until"])
    return pd.concat(rows, ignore_index=True)
