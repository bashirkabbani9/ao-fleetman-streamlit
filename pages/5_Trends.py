"""What the VOR history is telling you."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import brand
from lib.data import active_fleet, apply_depot, closed_vor, load_all, open_vor
from lib.ui import chart, page, panel_close, panel_open, sidebar_filter

page("Trends")
depot = sidebar_filter()
data = load_all()
today = data["today"]

vor = apply_depot(data["vor"], depot)
closed = closed_vor(vor)
active = active_fleet(apply_depot(data["vehicles"], depot))

st.title("Trends")
st.caption(f"{depot}. Based on {len(closed):,} finished VOR jobs over the last 12 months.")

if closed.empty:
    st.warning("No finished VOR records for this depot, so there is nothing to compare against.")
    st.stop()

# ---------------------------------------------------------- headline findings
last90 = closed[closed["vor_date"] >= today - pd.Timedelta(days=90)]
prev90 = closed[(closed["vor_date"] >= today - pd.Timedelta(days=180))
                & (closed["vor_date"] < today - pd.Timedelta(days=90))]

findings = []
if len(last90) >= 10 and len(prev90) >= 10:
    a = last90.groupby("depot")["days_off_road"].median()
    b = prev90.groupby("depot")["days_off_road"].median()
    counts = last90.groupby("depot").size()
    movers = pd.DataFrame({"now": a, "before": b, "n": counts}).dropna()
    movers = movers[movers["n"] >= 5]
    movers["change"] = movers["now"] - movers["before"]
    if not movers.empty:
        worst = movers.sort_values("change", ascending=False).iloc[0]
        if worst["change"] > 0:
            findings.append(
                f"**{worst.name}** is getting slower. Median days off road went from "
                f"{worst['before']:.0f} to {worst['now']:.0f} comparing the last 90 days "
                f"with the 90 before, across {int(worst['n'])} jobs."
            )

lost = closed.groupby("vor_sub_category")["days_off_road"].agg(["sum", "size", "median"])
if not lost.empty:
    top = lost.sort_values("sum", ascending=False).iloc[0]
    findings.append(
        f"**{top.name}** costs the most time: {int(top['sum'])} days lost across "
        f"{int(top['size'])} jobs, median {top['median']:.0f} days each."
    )

late = closed["late_vs_promise"].mean() * 100
findings.append(
    f"**{late:.0f}% of jobs came back later than first promised.** Treat the supplier ETA "
    "as an opening offer rather than a plan."
)

panel_open("What this is telling you", "Computed from the data, not written in advance")
for f in findings:
    st.markdown(f"- {f}")
panel_close()

# ----------------------------------------------------------------- over time
c1, c2 = st.columns(2)
monthly = closed.groupby("month").agg(events=("reg", "size"), median=("days_off_road", "median"))
monthly = monthly.sort_index()

with c1:
    panel_open("VOR events per month", "With a three month moving average")
    ma = monthly["events"].rolling(3, min_periods=1).mean()
    fig = go.Figure()
    fig.add_bar(x=monthly.index, y=monthly["events"], name="Events", marker_color=brand.STEAM)
    fig.add_scatter(x=monthly.index, y=ma, name="3 month average", mode="lines",
                    line=dict(color=brand.ICE, width=3))
    fig.update_layout(**brand.PLOT_LAYOUT, height=300)
    chart(fig)
    panel_close()

with c2:
    panel_open("Median days off road per month", "How long a job takes, over time")
    fig = go.Figure(go.Scatter(
        x=monthly.index, y=monthly["median"], mode="lines+markers",
        line=dict(color=brand.HEAT, width=3), marker=dict(size=7),
    ))
    fig.update_layout(**brand.PLOT_LAYOUT, height=300, showlegend=False)
    chart(fig)
    panel_close()

# ------------------------------------------------------------- sub categories
panel_open("By fault", "Ranked by total days lost, which is what actually costs the fleet")
sub = closed.groupby("vor_sub_category").agg(
    events=("reg", "size"), median=("days_off_road", "median"),
    total=("days_off_road", "sum"),
).sort_values("total", ascending=False)
st.dataframe(pd.DataFrame({
    "Fault": sub.index,
    "Jobs": sub["events"].values,
    "Median days": sub["median"].round(0).astype(int).values,
    "Total days lost": sub["total"].astype(int).values,
}), hide_index=True, width="stretch", height=340)
panel_close()

# -------------------------------------------------------------------- depots
d1, d2 = st.columns(2)
with d1:
    panel_open("By depot", "Events per 100 vehicles and the 90 day direction")
    fleet = active.groupby("depot").size()
    ev = closed.groupby("depot").size()
    med = closed.groupby("depot")["days_off_road"].median()
    a = last90.groupby("depot")["days_off_road"].median()
    b = prev90.groupby("depot")["days_off_road"].median()
    dep = pd.DataFrame({"fleet": fleet, "events": ev, "median": med, "now": a, "before": b}).dropna(subset=["fleet"])
    dep = dep[dep["fleet"] > 0]
    dep["per100"] = dep["events"].fillna(0) / dep["fleet"] * 100
    dep["change"] = dep["now"] - dep["before"]

    def arrow(v):
        if pd.isna(v):
            return "not enough jobs"
        if v > 0.5:
            return f"worse by {v:.0f} days"
        if v < -0.5:
            return f"better by {abs(v):.0f} days"
        return "steady"

    dep = dep.sort_values("change", ascending=False)
    st.dataframe(pd.DataFrame({
        "Depot": dep.index,
        "Fleet": dep["fleet"].astype(int).values,
        "Jobs per 100": dep["per100"].round(1).values,
        "Median days": dep["median"].round(0).values,
        "Last 90 days": [arrow(v) for v in dep["change"]],
    }), hide_index=True, width="stretch", height=420)
    panel_close()

with d2:
    panel_open("By repair site", "Do they hit the date they first gave you")
    site = closed.groupby("repair_site").agg(
        jobs=("reg", "size"), median=("days_off_road", "median"),
        late=("late_vs_promise", "mean"),
    )
    site["on_time"] = (1 - site["late"]) * 100
    site["too_few"] = site["jobs"] < 8
    site = site.sort_values(["too_few", "on_time"], ascending=[True, True])
    st.dataframe(pd.DataFrame({
        "Repair site": site.index,
        "Jobs": site["jobs"].values,
        "Median days": site["median"].round(0).values,
        "Hit first ETA": [("too few to judge" if few else f"{v:.0f}%")
                          for v, few in zip(site["on_time"], site["too_few"])],
    }), hide_index=True, width="stretch", height=420)
    panel_close()

# ------------------------------------------------------- liability and repeats
l1, l2 = st.columns(2)
with l1:
    panel_open("Who carries the cost", "Events and total days lost by liability")
    li = closed.groupby("liability").agg(events=("reg", "size"), days=("days_off_road", "sum"))
    li = li.sort_values("days", ascending=False)
    fig = go.Figure()
    fig.add_bar(x=li.index, y=li["days"], name="Days lost", marker_color=brand.JAM)
    fig.add_bar(x=li.index, y=li["events"], name="Jobs", marker_color=brand.TOAST)
    fig.update_layout(**brand.PLOT_LAYOUT, barmode="group", height=290)
    chart(fig)
    panel_close()

with l2:
    panel_open("Mechanical against body", "Jobs per month by damage type")
    dmg = closed.pivot_table(index="month", columns="damage_type", values="reg", aggfunc="size").fillna(0)
    fig = go.Figure()
    for i, col in enumerate(dmg.columns):
        fig.add_scatter(x=dmg.index, y=dmg[col], name=col, mode="lines",
                        line=dict(color=[brand.ICE, brand.TOAST][i % 2], width=3))
    fig.update_layout(**brand.PLOT_LAYOUT, height=290)
    chart(fig)
    panel_close()

panel_open("Repeat offenders", "Three or more VOR events in the last 12 months")
rep = vor.groupby("reg").agg(
    events=("vor_date", "size"), days=("days_off_road", "sum"), depot=("depot", "first"),
)
rep = rep[rep["events"] >= 3].sort_values(["days", "events"], ascending=False)
if rep.empty:
    st.info("No vehicle has been off the road three or more times.")
else:
    st.dataframe(pd.DataFrame({
        "Reg": rep.index,
        "Depot": rep["depot"].values,
        "VOR events": rep["events"].values,
        "Total days lost": rep["days"].astype(int).values,
    }).head(25), hide_index=True, width="stretch")
panel_close()
