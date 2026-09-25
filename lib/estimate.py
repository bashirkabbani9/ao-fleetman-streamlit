"""Predicting when a vehicle under repair comes back.

Same method as the Base44 build, so the two agree. Find the closest comparable
set of finished jobs, take the median of how long they actually took, and say
what the answer is based on. A number with no stated basis is not useful.
"""
import numpy as np
import pandas as pd

MIN_SAMPLE = 5


def _confidence(n):
    if n >= 20:
        return "Good"
    if n >= 8:
        return "Fair"
    return "Weak"


def predict_return(record, closed, today):
    """record: a Series for one open VOR row. closed: finished VOR rows."""
    sub = record.get("vor_sub_category")
    cat = record.get("vor_category")
    site = record.get("repair_site")

    pool = closed[closed["days_off_road"].notna() & (closed["days_off_road"] >= 0)]

    # Most specific comparison set that still has enough jobs to mean anything.
    candidates = [
        (pool[(pool["vor_sub_category"] == sub) & (pool["repair_site"] == site)],
         lambda n: f"based on {n} past {sub} jobs at {site}"),
        (pool[pool["vor_sub_category"] == sub],
         lambda n: f"based on {n} past {sub} jobs, all sites"),
        (pool[pool["vor_category"] == cat],
         lambda n: f"based on {n} past {cat} jobs, all sub-categories"),
        (pool, lambda n: f"based on {n} past VOR jobs, all categories"),
    ]
    rows, label = next(((r, l) for r, l in candidates if len(r) >= MIN_SAMPLE), candidates[-1])

    days = rows["days_off_road"].to_numpy()
    n = len(days)
    days_off = record.get("days_off_road")
    supplier = record.get("expected_return_date")

    out = {
        "predicted_return": pd.NaT,
        "basis": label(n) if n else "no comparable finished jobs in the history yet",
        "confidence": _confidence(n),
        "sample_size": n,
        "median_days": None,
        "p80_days": None,
        "days_off_so_far": days_off,
        "used_percentile": None,
        "beyond_comparable": False,
        "vs_supplier_days": None,
        "disagreement": False,
    }
    if n == 0 or pd.isna(record.get("vor_date")):
        return out

    med = int(np.median(days))
    p80 = int(np.percentile(days, 80, method="nearest"))
    out["median_days"], out["p80_days"] = med, p80

    start = record["vor_date"]
    used, predicted = 50, start + pd.Timedelta(days=med)

    # Once a job passes the typical duration, the typical duration is no longer the
    # right answer. Move to the slow end, and past that admit we cannot say.
    if days_off is not None and not pd.isna(days_off) and days_off > med:
        used, predicted = 80, start + pd.Timedelta(days=p80)
        if days_off > p80:
            out["beyond_comparable"] = True
            predicted = pd.NaT

    out["used_percentile"] = used
    out["predicted_return"] = predicted
    if not pd.isna(predicted) and not pd.isna(supplier):
        diff = (predicted - supplier).days
        out["vs_supplier_days"] = diff
        out["disagreement"] = abs(diff) > 3
    return out


def estimate_open(open_rows, closed, today):
    """Vectorised enough for a few hundred open jobs. Returns one frame."""
    if open_rows.empty:
        return pd.DataFrame(
            columns=["predicted_return", "basis", "confidence", "sample_size",
                     "median_days", "p80_days", "vs_supplier_days", "disagreement",
                     "beyond_comparable", "used_percentile"]
        )
    results = [predict_return(row, closed, today) for _, row in open_rows.iterrows()]
    est = pd.DataFrame(results, index=open_rows.index)
    est["predicted_return"] = pd.to_datetime(est["predicted_return"])
    return est
