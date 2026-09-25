"""Shared chrome: theme CSS, stat tiles, status pills, and the demo action buttons."""
import inspect
import pandas as pd
import streamlit as st

from lib import brand
from lib.data import load_all

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Figtree:wght@400;600;800&display=swap');

html, body, [class*="css"], .stApp {{
    font-family: 'Figtree', ui-sans-serif, system-ui, sans-serif;
}}
.stApp {{ background: #FBFDFC; }}
h1, h2, h3, h4 {{ color: {brand.GREEN_DARK}; font-weight: 800; letter-spacing: -0.01em; }}

/* Stat tile */
.ao-tile {{
    background: #FFFFFF;
    border: 1px solid {brand.GRID};
    border-radius: 18px;
    padding: 18px 20px;
    box-shadow: 0 2px 12px -2px rgba(2,66,43,0.08);
    height: 100%;
}}
.ao-tile .lbl {{
    font-size: 12px; font-weight: 700; letter-spacing: 0.04em;
    text-transform: uppercase; color: {brand.MUTED};
}}
.ao-tile .val {{ font-size: 34px; font-weight: 800; line-height: 1.1; margin-top: 4px; }}
.ao-tile .sub {{ font-size: 12px; color: {brand.MUTED}; margin-top: 4px; }}

/* Panels */
.ao-panel {{
    background: #FFFFFF;
    border: 1px solid {brand.GRID};
    border-radius: 18px;
    padding: 18px 20px 6px 20px;
    box-shadow: 0 2px 12px -2px rgba(2,66,43,0.08);
    margin-bottom: 4px;
}}
.ao-panel h4 {{ margin: 0; font-size: 15px; }}
.ao-panel .sub {{ font-size: 12px; color: {brand.MUTED}; margin: 2px 0 10px 0; }}

/* Status pills */
.pill {{
    display: inline-block; padding: 2px 10px; border-radius: 999px;
    font-size: 11px; font-weight: 700;
}}
.pill-active {{ background: {brand.GREEN_LIGHT}; color: {brand.GREEN_DARK}; }}
.pill-vor {{ background: {brand.SIMMER}; color: {brand.BURN}; }}
.pill-removed {{ background: #ECF1EE; color: {brand.MUTED}; }}

.ao-banner {{
    background: {brand.BREAD}; border: 1px solid {brand.TOAST};
    color: {brand.BURN}; border-radius: 14px; padding: 10px 14px;
    font-size: 13px; margin-bottom: 14px;
}}

section[data-testid="stSidebar"] {{ background: {brand.GREEN_DARK}; }}
section[data-testid="stSidebar"] * {{ color: #DFF3E6; }}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 {{ color: #FFFFFF; }}

div[data-testid="stDataFrame"] {{ border-radius: 14px; overflow: hidden; }}
</style>
"""


def page(title, icon="AO"):
    st.set_page_config(page_title=f"{title} | AO Fleetman", page_icon="AO", layout="wide")
    st.markdown(CSS, unsafe_allow_html=True)


def tile(col, label, value, sub=None, tone="dark"):
    colour = {
        "dark": brand.GREEN_DARK,
        "green": brand.GREEN_DARK,
        "heat": brand.HEAT,
        "toast": brand.TOAST,
        "ice": brand.ICE,
    }[tone]
    col.markdown(
        f"""<div class="ao-tile"><div class="lbl">{label}</div>
        <div class="val" style="color:{colour}">{value}</div>
        <div class="sub">{sub or "&nbsp;"}</div></div>""",
        unsafe_allow_html=True,
    )


def panel_open(title, subtitle=None):
    st.markdown(
        f"""<div class="ao-panel"><h4>{title}</h4>
        <div class="sub">{subtitle or "&nbsp;"}</div>""",
        unsafe_allow_html=True,
    )


def panel_close():
    st.markdown("</div>", unsafe_allow_html=True)


def sidebar_filter():
    """Global depot filter, shared by every page through session state."""
    data = load_all()
    names = sorted(data["depots"]["name"].dropna().unique().tolist())
    options = ["All depots"] + names
    current = st.session_state.get("depot_filter", "All depots")
    if current not in options:
        current = "All depots"

    with st.sidebar:
        st.markdown("### AO Fleetman")
        st.caption("Internal operations tool, AO Transport")
        choice = st.selectbox("Depot", options, index=options.index(current), key="depot_filter")
        st.caption(
            f"Data as at {data['today']:%d %b %Y}. Sample data, fictional, for demonstration."
        )
    return choice


def demo_action(label, key, icon=None, kind="secondary", width=None):
    """An action button that looks real and says plainly that it is not wired up.

    The write side of this app lives in the Base44 build. This version is read only
    on purpose, so the buttons are here to show the shape of the tool, not to work.
    """
    kwargs = {"key": key, "type": kind}
    if icon:
        kwargs["icon"] = icon
    if width:
        kwargs["width"] = "stretch"
    if st.button(label, **kwargs):
        st.toast(f"{label} is not wired up in this read-only demo", icon=":material/info:")
    return False


def status_pill(status):
    cls = {"Active": "pill-active", "VOR": "pill-vor", "Removed": "pill-removed"}.get(status, "pill-removed")
    return f'<span class="pill {cls}">{status}</span>'


def fmt_date(value):
    if value is None or pd.isna(value):
        return "-"
    return pd.Timestamp(value).strftime("%d %b %Y")


def empty_notice(message):
    st.markdown(f'<div class="ao-banner">{message}</div>', unsafe_allow_html=True)

# st.plotly_chart gained `width` in some versions and takes `use_container_width` in
# others. Passing the wrong one does not raise, it silently forwards the value to
# Plotly and the chart never stretches, so decide once from the actual signature.
_PLOTLY_WIDTH_KW = (
    "width" if "width" in inspect.signature(st.plotly_chart).parameters
    else "use_container_width"
)
_PLOTLY_WIDTH_VAL = "stretch" if _PLOTLY_WIDTH_KW == "width" else True


def chart(fig, height=None):
    """Render a Plotly figure full width, on whichever Streamlit version is installed."""
    if height is not None:
        fig.update_layout(height=height)
    st.plotly_chart(
        fig,
        config={"displayModeBar": False},
        **{_PLOTLY_WIDTH_KW: _PLOTLY_WIDTH_VAL},
    )
