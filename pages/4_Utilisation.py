"""Was the fleet actually used, and what did standing still cost."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from lib import brand
from lib.data import apply_depot, load_all
from lib.ui import chart, page, panel_close, panel_open, sidebar_filter, tile

page("Utilisation")
depot = sidebar_filter()
data = load_all()

transport = apply_depot(data["transport"], depot)
vehicles = data["vehicles"].set_index("reg")

st.title("Utilisation")
st.caption(
    f"{depot}. The transport log covers the delivery fleet. A vehicle counts as utilised "
    "when it was out for delivery or on a reload."
)

if transport.empty:
    st.warning("No transport log rows for this depot.")
    st.stop()

daily = transport.groupby("log_date").agg(fleet=("reg", "size"), used=("utilised", "sum")).reset_index()
daily["pct"] = daily["used"] / daily["fleet"] * 100
latest = daily.iloc[-1]

# Only hire vehicles are counted here. An owned or leased vehicle costs the same
# whether it moves or not, so including it would overstate the cost of standing still.
latest_rows = transport[transport["log_date"] == latest["log_date"]]
stood = latest_rows[~latest_rows["utilised"]].copy()
stood["weekly_hire_charge"] = stood["reg"].map(vehicles["weekly_hire_charge"]).fillna(0)
stood["ownership"] = stood["reg"].map(vehicles["ownership"])
hire_stood = stood[stood["ownership"] == "Hire"]
weekly_cost = float(hire_stood["weekly_hire_charge"].sum())

t = st.columns(4)
tile(t[0], "Utilised", f"{latest['pct']:.0f}%", f"on {latest['log_date']:%d %b %Y}", "green")
tile(t[1], "Out of", f"{int(latest['used'])}/{int(latest['fleet'])}", "delivery fleet vehicles")
tile(t[2], "Hire vehicles stood", f"{len(hire_stood):,}", "not used that day", "ice")
tile(t[3], "Cost of standing still", f"£{weekly_cost:,.0f}", "per week, hire charges only", "heat")

st.write("")
panel_open("Utilisation by day", "Share of the delivery fleet that moved")
fig = go.Figure(go.Bar(
    x=daily["log_date"], y=daily["pct"], marker_color=brand.GREEN,
    text=[f"{p:.0f}%" for p in daily["pct"]], textposition="outside",
    textfont=dict(color=brand.MUTED, size=11),
    hovertemplate="%{x|%a %d %b}: %{y:.1f}%<extra></extra>",
))
fig.update_layout(**brand.PLOT_LAYOUT, height=280, showlegend=False)
fig.update_yaxes(ticksuffix="%", range=[0, 105])
chart(fig)
panel_close()

c1, c2 = st.columns([3, 2])
with c1:
    panel_open("By depot", f"Most recent day: {latest['log_date']:%d %b %Y}")
    by = latest_rows.groupby("depot").agg(
        fleet=("reg", "size"),
        utilised=("utilised", "sum"),
    )
    by["stood"] = by["fleet"] - by["utilised"]
    by["off_road"] = latest_rows[latest_rows["status"] == "VOR"].groupby("depot").size()
    by["off_road"] = by["off_road"].fillna(0).astype(int)
    by["pct"] = by["utilised"] / by["fleet"] * 100
    by = by.sort_values("pct")
    st.dataframe(pd.DataFrame({
        "Depot": by.index,
        "Fleet": by["fleet"].values,
        "Utilised": by["utilised"].values,
        "Stood": by["stood"].values,
        "Off road": by["off_road"].values,
        "Utilisation": [f"{p:.0f}%" for p in by["pct"]],
    }), hide_index=True, width="stretch", height=430)
    panel_close()

with c2:
    panel_open("Status mix", f"All {len(transport):,} logged vehicle days")
    mix = transport["status"].value_counts()
    palette = {
        "Out for Delivery": brand.GREEN, "RELOAD PT 2": brand.GREEN_LIGHT,
        "Stood Not Utilised": brand.ICE, "Stood": brand.STEAM,
        "VOR": brand.HEAT, "Not Recorded": brand.GRID,
    }
    fig = go.Figure(go.Bar(
        x=mix.values, y=mix.index, orientation="h",
        marker_color=[palette.get(s, brand.JAM) for s in mix.index],
        text=mix.values, textposition="outside", textfont=dict(color=brand.MUTED, size=11),
    ))
    fig.update_layout(**brand.PLOT_LAYOUT, height=300, showlegend=False)
    fig.update_xaxes(range=[0, mix.max() * 1.2])
    chart(fig)
    st.caption(
        "Owned and leased vehicles are excluded from the cost figure. Their charge does not "
        "vary with use, so counting them would overstate what standing still costs."
    )
    panel_close()
