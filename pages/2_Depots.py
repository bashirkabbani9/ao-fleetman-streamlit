"""Depot comparison."""
import pandas as pd
import streamlit as st

from lib import brand
from lib.data import active_fleet, load_all, open_vor
from lib.ui import page, panel_close, panel_open, sidebar_filter

page("Depots")
sidebar_filter()
data = load_all()

st.title("Depots")
st.caption("Every depot, ranked by how much of its fleet is off the road.")

active = active_fleet(data["vehicles"])
openv = open_vor(data["vor"])

summary = pd.DataFrame({
    "fleet": active.groupby("depot").size(),
    "off": openv.groupby("depot").size(),
}).fillna(0)
summary = summary[summary["fleet"] > 0]
summary["pct"] = summary["off"] / summary["fleet"] * 100
summary = summary.sort_values("pct", ascending=False)

fleet_pct = len(openv) / len(active) * 100 if len(active) else 0
st.caption(f"Fleet wide, {len(openv)} of {len(active)} vehicles are off the road, which is {fleet_pct:.1f}%.")

cols = st.columns(3)
for i, (name, row) in enumerate(summary.iterrows()):
    with cols[i % 3]:
        worse = row["pct"] > fleet_pct
        colour = brand.HEAT if worse else brand.GREEN_DARK
        types = (active[active["depot"] == name]["vehicle_type"]
                 .value_counts().head(4))
        breakdown = ", ".join(f"{n} {t}" for t, n in types.items())
        st.markdown(
            f"""<div class="ao-tile" style="margin-bottom:14px">
            <div style="display:flex;justify-content:space-between;align-items:baseline">
              <div style="font-weight:800;font-size:16px;color:{brand.GREEN_DARK}">{name}</div>
              <div style="font-size:22px;font-weight:800;color:{colour}">{row['pct']:.1f}%</div>
            </div>
            <div class="sub">{int(row['fleet'])} vehicles, {int(row['off'])} off the road</div>
            <div class="sub" style="margin-top:6px">{breakdown}</div>
            <div style="height:6px;border-radius:999px;background:{brand.GRID};margin-top:10px">
              <div style="height:6px;border-radius:999px;background:{colour};
                          width:{min(100, row['pct'] / max(summary['pct'].max(), 1) * 100):.0f}%"></div>
            </div>
            </div>""",
            unsafe_allow_html=True,
        )
