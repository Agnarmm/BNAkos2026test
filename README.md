# Live midterm results → CSV for Datawrapper

A GitHub Action fetches civicAPI every 5 minutes and writes two flat CSVs:

- `data/senate.csv` – one row per state (all 50)
- `data/house.csv` – one row per district (`AZ-01`, `AK-AL`, …)

Columns: `id, state, postal, status, leader, leader_party, leader_pct, runner_up,
runner_up_party, runner_up_pct, margin_pts, pct_reporting, called, updated_utc`

`status` is one of: `Dem win`, `Rep win`, `Ind win`, `Dem lead`, `Rep lead`, `Ind lead`,
`Too early`, `No race`.

## Setup (about 10 minutes)

1. **Create a public repo** on GitHub (must be public for Datawrapper to read it).
2. **Upload this folder's contents**, keeping the `.github/workflows/` folder.
   (On github.com: "Add file → Upload files", drag everything in, commit.)
3. **Allow the Action to push:** Settings → Actions → General → Workflow permissions →
   "Read and write permissions" → Save.
4. **Run it once:** Actions tab → "Update election CSVs" → "Run workflow".
   After that it runs every 5 minutes on its own.
5. **Your CSV URL** is:
   `https://raw.githubusercontent.com/YOUR-USER/YOUR-REPO/main/data/senate.csv`

## Datawrapper

1. New Map → Choropleth map → **USA » States** (or the hexagon tile map).
2. Upload data → **Link external dataset** → paste the raw URL above.
3. Match on the `state` column (full state names), and color by `status`
   using categories:
   - Dem win `#1f4e9c` · Dem lead `#8fb3e6`
   - Rep win `#c0262d` · Rep lead `#f2a3a0`
   - Ind win `#6a4c93` · Ind lead `#c5b3e0`
   - Too early `#d9d9d9` · No race `#f4f4f4`
4. Tooltip: `{{ leader }} ({{ leader_party }}) {{ leader_pct }}% · {{ pct_reporting }}% reporting`
5. Notes: "Unofficial results via civicAPI (civicapi.org). Updated {{ updated_utc }}."
   (civicAPI requires attribution.)

## Styling before results arrive

`data/demo_senate.csv` has fake results. Paste or upload it into a *copy* of your map
to set up colors and tooltips, then switch the real map to the live URL. **The demo
data is fake** – never publish it. (`python scripts/build_csv.py --demo` makes a new one.)

## Things to know

- Before polls close, civicAPI may serve *test* data; the script ignores it, so
  every state shows "Too early". (`--test` accepts it if you want to try it.)
- States with no Senate race only show "No race" once civicAPI's real document is
  live; until then they show "Too early".
- GitHub's 5-minute schedule can run late on busy nights, and raw GitHub files are
  cached for a few minutes, so expect results 5–15 minutes behind live TV.
- Race calls come from civicAPI's `winner` flag. Treat them as unofficial.
- The civicAPI document IDs (Senate 87528, House 87524) are at the top of
  `scripts/build_csv.py`, taken from another 2026 tracker that uses them. If the
  Action log says "no document returned", check civicAPI's search for the right IDs.
