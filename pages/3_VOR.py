"""Live vehicles off the road, with the history based return estimate."""
import pandas as pd
import streamlit as st

from lib import brand
from lib.data import active_fleet, apply_depot, closed_vor, load_all, open_vor
from lib.estimate import estimate_open
from lib.ui import demo_action, page, panel_close, panel_open, sidebar_filter, tile

page("VOR")
depot = sidebar_filter()
data = load_all()
today = data["today"]

vor = apply_depot(data["vor"], depot)
openv = open_vor(vor).copy()
closed = closed_vor(data["vor"])
active = active_fleet(apply_depot(data["vehicles"], depot))

st.title("Vehicles off the road")
st.caption(f"{depot}. Days off road is counted live, not read from the source sheet.")

if openv.empty:
    st.success("Nothing is off the road for this depot.")
    st.stop()

est = estimate_open(openv, closed, today)
joined = openv.join(est)

t = st.columns(4)
tile(t[0], "Off road", f"{len(openv):,}", "open VOR records", "heat")
tile(t[1], "Share of fleet", f"{len(openv) / len(active) * 100:.1f}%" if len(active) else "-",
     f"of {len(active):,} active vehicles", "heat")
tile(t[2], "Past supplier ETA", f"{int(openv['overdue'].sum()):,}", "promised back already", "heat")
tile(t[3], "Median days off", f"{int(openv['days_off_road'].median()):,}", "across open jobs")

st.write("")
f = st.columns(5)
cats = ["All"] + sorted(openv["vor_category"].dropna().unique().tolist())
subs = ["All"] + sorted(openv["vor_sub_category"].dropna().unique().tolist())
liabs = ["All"] + sorted(openv["liability"].dropna().unique().tolist())
dmgs = ["All"] + sorted(openv["damage_type"].dropna().unique().tolist())
c = f[0].selectbox("Category", cats)
sc = f[1].selectbox("Fault", subs)
lb = f[2].selectbox("Liability", liabs)
dm = f[3].selectbox("Damage", dmgs)
only_late = f[4].checkbox("Overdue only", value=False)

view = joined
if c != "All":
    view = view[view["vor_category"] == c]
if sc != "All":
    view = view[view["vor_sub_category"] == sc]
if lb != "All":
    view = view[view["liability"] == lb]
if dm != "All":
    view = view[view["damage_type"] == dm]
if only_late:
    view = view[view["overdue"]]

view = view.sort_values("days_off_road", ascending=False)
st.caption(f"{len(view):,} of {len(joined):,} open records")

table = pd.DataFrame({
    "Reg": view["reg"],
    "Depot": view["depot"],
    "Type": view["vehicle_type"],
    "Off road": view["vor_date"].dt.strftime("%d %b"),
    "Days off": view["days_off_road"],
    "Supplier ETA": view["expected_return_date"].dt.strftime("%d %b"),
    "Late by": view["days_vs_eta"].where(view["overdue"]).astype("Int64"),
    "Predicted": view.apply(
        lambda r: "beyond history" if r["beyond_comparable"] else (
            "-" if pd.isna(r["predicted_return"]) else r["predicted_return"].strftime("%d %b")), axis=1),
    "Vs supplier": view["vs_supplier_days"].astype("Float64").round(0).astype("Int64"),
    "Confidence": view["confidence"],
    "Fault": view["vor_sub_category"],
    "Site": view["repair_site"],
    "Liability": view["liability"],
    "Told supplier": view["reported_to_supplier"].map({True: "Yes", False: "No"}),
    "Based on": view["basis"],
}).reset_index(drop=True)

st.dataframe(
    table, hide_index=True, width="stretch", height=520,
    column_config={
        "Days off": st.column_config.NumberColumn(help="Today minus the date it went off the road"),
        "Late by": st.column_config.NumberColumn("Late by", help="Days past the supplier ETA"),
        "Vs supplier": st.column_config.NumberColumn(
            help="Positive means history says it comes back later than the supplier promised"),
        "Based on": st.column_config.TextColumn(width="medium"),
    },
)

a = st.columns(4)
with a[0]:
    demo_action("Take a vehicle off road", "vor_add", icon=":material/build:", kind="primary", width=True)
with a[1]:
    demo_action("Return to service", "vor_ret", icon=":material/check:", width=True)
with a[2]:
    demo_action("Update ETA", "vor_eta", icon=":material/schedule:", width=True)
with a[3]:
    st.download_button("Download as CSV", table.to_csv(index=False).encode("utf8"),
                       file_name="ao_vor.csv", mime="text/csv",
                       icon=":material/download:", width="stretch")
