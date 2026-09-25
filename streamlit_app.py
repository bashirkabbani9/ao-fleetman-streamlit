"""AO Fleetman, Streamlit build. Dashboard is the entry page."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import brand
from lib.data import (COMPLIANCE_CHECKS, active_fleet, apply_depot, closed_vor,
                      compliance_frame, load_all, open_vor)
from lib.estimate import estimate_open
from lib.ui import chart, demo_action, page, panel_close, panel_open, sidebar_filter, tile

page("Dashboard")
depot = sidebar_filter()
data = load_all()
today = data["today"]

vehicles = apply_depot(data["vehicles"], depot)
vor = apply_depot(data["vor"], depot)
transport = apply_depot(data["transport"], depot)

active = active_fleet(vehicles)
openv = open_vor(vor)
closed = closed_vor(data["vor"])          # history is fleet wide, so estimates stay comparable
est = estimate_open(openv, closed, today)

st.title("Dashboard")
st.caption(f"{depot}. Every figure recalculates against today, {today:%d %B %Y}.")

head = st.columns([1, 1, 1, 1, 1, 1])
vor_pct = (len(openv) / len(active) * 100) if len(active) else 0
overdue = int(openv["overdue"].sum()) if not openv.empty else 0
miss = int(est["disagreement"].sum()) if not est.empty and "disagreement" in est else 0
if not est.empty:
    miss = int(((est["vs_supplier_days"].notna()) & (est["vs_supplier_days"] > 3)).sum())

latest_day = transport["log_date"].max() if not transport.empty else None
today_rows = transport[transport["log_date"] == latest_day] if latest_day is not None else transport.iloc[0:0]
util_pct = (today_rows["utilised"].sum() / len(today_rows) * 100) if len(today_rows) else 0

comp = compliance_frame(active, today)
comp_overdue = int((comp["days_until"] < 0).sum()) if not comp.empty else 0

tile(head[0], "Active fleet", f"{len(active):,}", f"{len(vehicles):,} records in total")
tile(head[1], "Off road now", f"{len(openv):,}", f"{vor_pct:.1f}% of the active fleet", "heat")
tile(head[2], "Past supplier ETA", f"{overdue:,}", "already later than promised", "heat")
tile(head[3], "Predicted to miss ETA", f"{miss:,}", "history says later than the supplier", "toast")
tile(head[4], "Utilised", f"{util_pct:.0f}%",
     f"delivery fleet on {latest_day:%d %b}" if latest_day is not None else "no transport log", "green")
tile(head[5], "Compliance overdue", f"{comp_overdue:,}", "checks already past due", "heat")

if vehicles.empty:
    st.warning("No vehicles for this depot.")
    st.stop()

st.write("")
left, right = st.columns([3, 2])

# VOR as a share of each depot's fleet. The percentage is what matters, not the count:
# Crewe always has the most vehicles off road simply because Crewe is the biggest site.
with left:
    panel_open("VOR by depot", "Off road as a percentage of that depot's fleet, worst first")
    base = active_fleet(data["vehicles"]).groupby("depot").size()
    off = open_vor(data["vor"]).groupby("depot").size()
    dep = pd.DataFrame({"fleet": base, "off": off}).fillna(0)
    dep = dep[dep["fleet"] > 0]
    dep["pct"] = dep["off"] / dep["fleet"] * 100
    dep = dep.sort_values("pct")
    fig = go.Figure(go.Bar(
        x=dep["pct"], y=dep.index, orientation="h",
        marker_color=brand.HEAT,
        text=[f"{int(o)} of {int(f)}" for o, f in zip(dep["off"], dep["fleet"])],
        textposition="outside", textfont=dict(color=brand.MUTED, size=11),
        hovertemplate="%{y}: %{x:.1f}% off road<extra></extra>",
    ))
    fig.update_layout(**brand.PLOT_LAYOUT, height=30 * len(dep) + 60, showlegend=False)
    fig.update_xaxes(title="", ticksuffix="%", range=[0, dep["pct"].max() * 1.35 if len(dep) else 1])
    chart(fig)
    panel_close()

with right:
    panel_open("Needs attention", "Each of these is somebody's next phone call")
    veh_idx = data["vehicles"].set_index("reg")
    not_reported = int((~openv["reported_to_supplier"]).sum()) if not openv.empty else 0
    rm_gap = 0
    if not openv.empty:
        cover = openv["reg"].map(veh_idx["rm_cover"]).fillna(False)
        rm_gap = int((cover & ~openv["covered_under_rm"]).sum())
    comp_soon = comp[(comp["days_until"] >= 0) & (comp["days_until"] <= 14)] if not comp.empty else comp
    off_and_due = 0
    if not openv.empty and not comp_soon.empty:
        off_and_due = comp_soon[comp_soon["reg"].isin(openv["reg"])]["reg"].nunique()

    for label, count, hint in [
        ("Not reported to the supplier", not_reported, "open VOR the supplier has not been told about"),
        ("Past the supplier ETA", overdue, "promised back, still off road"),
        ("Possible unclaimed R&M", rm_gap, "vehicle has R&M cover, the VOR is not marked as covered"),
        ("Off road with a check due", off_and_due, "compliance due within 14 days while off road"),
    ]:
        tone = brand.HEAT if count else brand.MUTED
        st.markdown(
            f"""<div style="display:flex;justify-content:space-between;align-items:baseline;
            padding:7px 0;border-bottom:1px solid {brand.GRID}">
            <div><div style="font-weight:700;color:{brand.GREEN_DARK};font-size:13px">{label}</div>
            <div style="font-size:11px;color:{brand.MUTED}">{hint}</div></div>
            <div style="font-size:24px;font-weight:800;color:{tone}">{count}</div></div>""",
            unsafe_allow_html=True,
        )
    panel_close()

st.write("")
c1, c2 = st.columns([3, 2])

with c1:
    panel_open("Longest off road right now", "Ten worst, with what the history predicts")
    if openv.empty:
        st.info("Nothing off road for this depot.")
    else:
        worst = openv.join(est).sort_values("days_off_road", ascending=False).head(10)
        show = pd.DataFrame({
            "Reg": worst["reg"],
            "Depot": worst["depot"],
            "Fault": worst["vor_sub_category"],
            "Days off": worst["days_off_road"],
            "Supplier ETA": worst["expected_return_date"].dt.strftime("%d %b"),
            "Predicted": worst["predicted_return"].dt.strftime("%d %b").fillna("beyond history"),
            "Based on": worst["basis"],
        })
        st.dataframe(show, hide_index=True, width="stretch")
    panel_close()

with c2:
    panel_open("Compliance", "Overdue against due within 30 days")
    rows = []
    for label, _ in COMPLIANCE_CHECKS:
        sub = comp[comp["check"] == label]
        rows.append({
            "check": label,
            "overdue": int((sub["days_until"] < 0).sum()),
            "soon": int(((sub["days_until"] >= 0) & (sub["days_until"] <= 30)).sum()),
        })
    cdf = pd.DataFrame(rows)
    fig = go.Figure()
    fig.add_bar(x=cdf["check"], y=cdf["overdue"], name="Overdue", marker_color=brand.HEAT)
    fig.add_bar(x=cdf["check"], y=cdf["soon"], name="Due in 30 days", marker_color=brand.TOAST)
    fig.update_layout(**brand.PLOT_LAYOUT, barmode="group", height=260)
    chart(fig)
    panel_close()

st.write("")
panel_open("Off the road against back in service", "Last 14 days")
window = today - pd.Timedelta(days=13)
days = pd.date_range(window, today, freq="D")
opened = data["vor"] if depot == "All depots" else vor
op = opened[opened["vor_date"].between(window, today)].groupby("vor_date").size().reindex(days, fill_value=0)
ret = opened[opened["actual_return_date"].between(window, today)].groupby("actual_return_date").size().reindex(days, fill_value=0)
fig = go.Figure()
fig.add_bar(x=days, y=op.values, name="Taken off road", marker_color=brand.HEAT)
fig.add_bar(x=days, y=ret.values, name="Back in service", marker_color=brand.GREEN)
fig.update_layout(**brand.PLOT_LAYOUT, barmode="group", height=250)
chart(fig)
net = int(op.sum() - ret.sum())
if net > 0:
    st.caption(f"{net} more vehicles went off the road than came back over the last 14 days.")
elif net < 0:
    st.caption(f"{abs(net)} more vehicles came back than went off the road over the last 14 days.")
else:
    st.caption("Off road and back in service balanced out over the last 14 days.")
panel_close()
