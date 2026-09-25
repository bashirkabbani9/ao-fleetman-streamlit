# AO Fleetman, Streamlit build

A read-only fleet operations view for AO Transport: the whole fleet, vehicles off the
road, depot comparison, utilisation, VOR trends, and a history based estimate of when
a vehicle under repair comes back.

**This build is read only on purpose.** Add, edit, remove, take off road and update ETA
buttons are present so the tool reads as complete, but they are not wired to anything
and say so when pressed. The write side lives in the Base44 build.

## Deploying

1. Push this folder to a GitHub repository.
2. On share.streamlit.io, pick the repo, set the main file to `streamlit_app.py`, deploy.
3. Nothing else. No secrets, no database, no MCP. The data is the CSV in `data/`.

Set the app to private and add viewers by email if it is going anywhere near a real
fleet list. Community Cloud has no other access control.

## Layout

```
streamlit_app.py     Dashboard, the entry page
pages/               Fleet, Depots, VOR, Utilisation, Trends
lib/brand.py         AO colours and the shared Plotly layout
lib/data.py          Loading, typing, and the derived VOR columns
lib/estimate.py      The repair return prediction
lib/ui.py            Theme CSS, stat tiles, panels, demo buttons
data/*.csv           The sample fleet
```

## The data

Fictional, generated to match the shape of the real AO exports: 1,378 vehicles across
19 depots, 561 VOR records of which 100 are currently open, and 4,808 transport log
rows covering eight days of the delivery fleet.

Two things worth knowing. The three source sheets did not agree with each other, so the
vehicle record is the single source of truth and VOR and transport rows reference it by
registration. And a year of closed VOR history was generated, because a live snapshot
alone gives the trends page and the estimate nothing to learn from.

Everything is calculated against the real current date, so days off road and compliance
counts move on their own as time passes.

## How the return estimate works

For each open job, find the closest set of finished jobs with at least 5 examples,
preferring the same fault at the same repair site, then the same fault anywhere, then
the same category, then everything. Take the median of how long those actually took.

Once a vehicle passes that median the estimate moves to the 80th percentile, and once it
passes that too the app says the job has run beyond anything comparable rather than
inventing a date. Every prediction shows what it is based on and how many jobs, with a
confidence of Good at 20 or more, Fair at 8 to 19, Weak below that.

The same method runs in the Base44 build, so the two agree.

## Swapping in real data

Change `load_all()` in `lib/data.py`. Everything downstream works off the same four
frames, so nothing else needs touching. Keep the column names.

One gap to close first: the real VOR export records the expected return date but not
the actual one, and the estimate is built on how long jobs really took. The transport
report already holds the answer, because a vehicle carries the VOR status on the days
it is off the road. The actual return is the first day after the VOR start where that
registration is no longer VOR.

## Running locally

```
pip install -r requirements.txt
streamlit run streamlit_app.py
```
