"""Fleet list and vehicle detail."""
import pandas as pd
import streamlit as st

from lib import brand
from lib.data import COMPLIANCE_CHECKS, apply_depot, closed_vor, load_all, open_vor
from lib.estimate import predict_return
from lib.ui import demo_action, fmt_date, page, panel_close, panel_open, sidebar_filter, status_pill

page("Fleet")
depot = sidebar_filter()
data = load_all()
today = data["today"]
vehicles = apply_depot(data["vehicles"], depot)

st.title("Fleet")

selected = st.session_state.get("selected_reg")

# ---------------------------------------------------------------- detail view
if selected and selected in set(data["vehicles"]["reg"]):
    v = data["vehicles"].set_index("reg").loc[selected]
    if st.button("Back to the fleet list", icon=":material/arrow_back:"):
        del st.session_state["selected_reg"]
        st.rerun()

    st.markdown(
        f"## {selected} &nbsp; {status_pill(v['status'])}", unsafe_allow_html=True
    )
    st.caption(f"{v['make']} {v['model']}, {v['vehicle_type']}, {v['depot']}")

    actions = st.columns(5)
    with actions[0]:
        demo_action("Edit", "act_edit", icon=":material/edit:", width=True)
    with actions[1]:
        if v["status"] == "VOR":
            demo_action("Return to service", "act_ret", icon=":material/check:", kind="primary", width=True)
        else:
            demo_action("Take off road (VOR)", "act_vor", icon=":material/build:", kind="primary", width=True)
    with actions[2]:
        demo_action("Update ETA", "act_eta", icon=":material/schedule:", width=True)
    with actions[3]:
        demo_action("Remove from fleet", "act_rm", icon=":material/delete:", width=True)

    # Live repair estimate, the reason this page exists
    if v["status"] == "VOR":
        rec = data["vor"][(data["vor"]["reg"] == selected) & (data["vor"]["status"] == "Open")]
        if not rec.empty:
            row = rec.iloc[0]
            e = predict_return(row, closed_vor(data["vor"]), today)
            panel_open("Off road: predicted return", e["basis"])
            m = st.columns(4)
            m[0].metric("Days off road", int(row["days_off_road"]))
            m[1].metric("Supplier ETA", fmt_date(row["expected_return_date"]))
            m[2].metric(
                "Predicted return",
                "beyond history" if e["beyond_comparable"] else fmt_date(e["predicted_return"]),
                delta=(None if e["vs_supplier_days"] is None
                       else f"{e['vs_supplier_days']:+d} days vs supplier"),
                delta_color="inverse",
            )
            m[3].metric("Confidence", e["confidence"], help=f"Sample size {e['sample_size']}")
            st.caption(
                f"{row['vor_category']}, {row['vor_sub_category']}. At {row['repair_site']}. "
                f"Liability {row['liability']}. "
                + (f"ETA revised {int(row['eta_revision_count'])} times." if row["eta_revision_count"] else "")
            )
            panel_close()

    g1, g2, g3 = st.columns(3)
    with g1:
        panel_open("Identity")
        for label, key in [("Registration", "reg"), ("Make", "make"), ("Model", "model"),
                           ("Type", "vehicle_type"), ("Year", "registration_year"),
                           ("Livery", "livery"), ("Payload kg", "payload_kg"),
                           ("Fleet group", "fleet_group")]:
            st.markdown(f"**{label}** &nbsp; {v.get(key, '-') if key != 'reg' else selected}",
                        unsafe_allow_html=True)
        panel_close()
    with g2:
        panel_open("Ownership and cost")
        for label, key in [("Ownership", "ownership"), ("Supplier", "supplier"),
                           ("Lease start", "hire_lease_start_date"), ("Lease term months", "lease_term_months"),
                           ("Lease cost", "lease_cost"), ("Weekly hire charge", "weekly_hire_charge"),
                           ("Odometer", "odometer_reading"), ("Units", "odometer_unit")]:
            val = v.get(key)
            if key == "hire_lease_start_date":
                val = fmt_date(val)
            st.markdown(f"**{label}** &nbsp; {'-' if pd.isna(val) else val}", unsafe_allow_html=True)
        panel_close()
    with g3:
        panel_open("Compliance", "Red is overdue, amber is due within 30 days")
        for label, col in COMPLIANCE_CHECKS:
            due = v.get(col)
            if pd.isna(due):
                st.markdown(f"**{label}** &nbsp; not applicable")
                continue
            days = (pd.Timestamp(due) - today).days
            colour = brand.HEAT if days < 0 else brand.TOAST if days <= 30 else brand.GREEN_DARK
            note = f"{abs(days)} days overdue" if days < 0 else f"in {days} days"
            st.markdown(
                f"**{label}** &nbsp; <span style='color:{colour};font-weight:700'>"
                f"{fmt_date(due)}</span> <span style='color:{brand.MUTED};font-size:12px'>({note})</span>",
                unsafe_allow_html=True,
            )
        panel_close()

    e1, e2 = st.columns(2)
    with e1:
        panel_open("Equipment")
        for label, key in [("Telematics", "telematics"), ("Provider", "telematics_provider"),
                           ("CCTV", "cctv"), ("Trailer tracker", "trailer_tracker"),
                           ("Gearbox", "gearbox_type"), ("Fuel", "fuel"),
                           ("Three seater", "three_seater"), ("Front tyres", "front_tyre_size"),
                           ("Rear tyres", "back_tyre_size")]:
            val = v.get(key)
            if isinstance(val, (bool,)):
                val = "Yes" if val else "No"
            st.markdown(f"**{label}** &nbsp; {'-' if pd.isna(val) else val}", unsafe_allow_html=True)
        panel_close()
    with e2:
        panel_open("Registrations")
        for label, key in [("Dart Charge", "dart_charge_registered"),
                           ("Congestion zone", "congestion_zone_registered"),
                           ("MerseyFlow", "merseyflow_registered"),
                           ("Insurance database", "insurance_database"),
                           ("R&M cover", "rm_cover")]:
            st.markdown(f"**{label}** &nbsp; {'Yes' if v.get(key) else 'No'}", unsafe_allow_html=True)
        panel_close()

    hist = data["vor"][data["vor"]["reg"] == selected].sort_values("vor_date", ascending=False)
    panel_open("VOR history", f"{len(hist)} records")
    if hist.empty:
        st.info("This vehicle has never been off the road.")
    else:
        st.dataframe(pd.DataFrame({
            "Off road": hist["vor_date"].dt.strftime("%d %b %Y"),
            "Back": hist["actual_return_date"].dt.strftime("%d %b %Y").fillna("still off road"),
            "Days": hist["days_off_road"],
            "Category": hist["vor_category"],
            "Fault": hist["vor_sub_category"],
            "Site": hist["repair_site"],
            "Liability": hist["liability"],
        }), hide_index=True, width="stretch")
    panel_close()

    logs = data["transport"][data["transport"]["reg"] == selected].sort_values("log_date", ascending=False)
    panel_open("Recent transport log", "Most recent days first")
    if logs.empty:
        st.info("No transport log rows for this vehicle. The log covers the delivery fleet only.")
    else:
        st.dataframe(pd.DataFrame({
            "Date": logs["log_date"].dt.strftime("%d %b %Y"),
            "Status": logs["status"],
            "Route": logs["route"],
            "Start": logs["start_time"],
            "End": logs["end_time"],
            "Drops": logs["drops_out"],
        }).head(20), hide_index=True, width="stretch")
    panel_close()
    st.stop()

# ------------------------------------------------------------------ list view
top = st.columns([4, 1])
top[0].caption(f"{depot}. Click a row to open the vehicle.")
with top[1]:
    demo_action("Add vehicle", "act_add", icon=":material/add:", kind="primary", width=True)

f = st.columns(5)
types = ["All"] + sorted(vehicles["vehicle_type"].dropna().unique().tolist())
owns = ["All"] + sorted(vehicles["ownership"].dropna().unique().tolist())
groups = ["All"] + sorted(vehicles["fleet_group"].dropna().unique().tolist())
states = ["All", "Active", "VOR", "Removed"]
t = f[0].selectbox("Type", types)
o = f[1].selectbox("Ownership", owns)
g = f[2].selectbox("Fleet group", groups)
s = f[3].selectbox("Status", states, index=0)
q = f[4].text_input("Search registration", placeholder="e.g. SA22")

view = vehicles.copy()
if t != "All":
    view = view[view["vehicle_type"] == t]
if o != "All":
    view = view[view["ownership"] == o]
if g != "All":
    view = view[view["fleet_group"] == g]
if s != "All":
    view = view[view["status"] == s]
else:
    view = view[view["status"] != "Removed"]
if q:
    view = view[view["reg"].str.contains(q.strip(), case=False, na=False)]

st.caption(f"{len(view):,} vehicles")

table = pd.DataFrame({
    "Reg": view["reg"],
    "Depot": view["depot"],
    "Type": view["vehicle_type"],
    "Make": view["make"],
    "Model": view["model"],
    "Ownership": view["ownership"],
    "Group": view["fleet_group"],
    "Status": view["status"],
    "MOT due": view["mot_due_date"].dt.strftime("%d %b %Y"),
    "Odometer": view["odometer_reading"],
}).reset_index(drop=True)

event = st.dataframe(
    table, hide_index=True, width="stretch", height=560,
    on_select="rerun", selection_mode="single-row",
)
if event.selection.rows:
    st.session_state["selected_reg"] = table.iloc[event.selection.rows[0]]["Reg"]
    st.rerun()

st.download_button(
    "Download this view as CSV",
    table.to_csv(index=False).encode("utf8"),
    file_name="ao_fleet_view.csv",
    mime="text/csv",
    icon=":material/download:",
)
