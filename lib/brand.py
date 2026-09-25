"""AO brand tokens, from the AO brand guidelines.

ON Green is a fill colour. At roughly 2.2:1 against white it fails as text,
so anything that has to be read uses DARK_GREEN.
"""

GREEN = "#12C35A"        # ON Green, primary
GREEN_LIGHT = "#BEFCC8"  # Light Green
GREEN_DARK = "#02422B"   # Dark Green, all body text and headings
HEAT = "#F96155"         # off road, overdue
SIMMER = "#FFD8D2"
BREAD = "#FFE3C2"
TOAST = "#FFA878"        # due soon, warning
JAM = "#422439"
STEAM = "#C8D1FF"
ICE = "#4A6DCE"          # stood, idle
BURN = "#60222F"
WATER = "#011F44"        # deep text, chart axes
WHITE = "#FFFFFF"

# Categorical series order for charts, chosen so neighbouring series stay apart.
SERIES = [GREEN, ICE, TOAST, HEAT, WATER, JAM, BURN, GREEN_LIGHT]

GRID = "#E3EDE8"
MUTED = "#5B7A6C"

PLOT_LAYOUT = dict(
    font=dict(family="Figtree, Inter, system-ui, sans-serif", color=GREEN_DARK, size=13),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=8, r=8, t=8, b=8),
    xaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED)),
    yaxis=dict(gridcolor=GRID, zerolinecolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED)),
    hoverlabel=dict(bgcolor=WHITE, bordercolor=GRID, font=dict(color=GREEN_DARK)),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=MUTED)),
)
