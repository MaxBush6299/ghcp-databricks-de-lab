# Lab: Automated Data Engineering with GitHub Copilot + Databricks

> **You are on the `lab` branch.** The completed reference (generated notebooks + full walkthrough) lives on [`main`](https://github.com/MaxBush6299/ghcp-databricks-de-lab/tree/main).

---

## What you'll build

A **Formula 1 medallion lakehouse** in Databricks — entirely through conversation with GitHub Copilot.

Starting from the latest Formula 1 CSV dataset (50+ files spanning 14+ seasons — it grows as new races are run), you'll end up with:

- A Unity Catalog hierarchy: `formula1.{raw, bronze, silver, gold}`
- 9 Bronze Delta tables with schema-merged, metadata-enriched ingestion
- 8 Silver tables with proper types, deduplication, and normalised team names
- A full **snowflake dimensional model** in Gold (7 dimensions, 1 bridge, 5 facts)
- A live **AI/BI dashboard** — Constructor wins, Driver wins, all-time leaderboards

You'll also discover two real data quality issues mid-lab and craft the prompts to fix them yourself — that's the point.

**Estimated time:** 60–90 minutes (most of it is watching Copilot work). If you customize the plan with extras like SCD-2 dimensions, additional fact tables, or a deeper snowflake, expect closer to 2–3 hours.

---

## Prerequisites checklist

Before you start, confirm:

- [ ] **GitHub Copilot** active in VS Code (Individual, Business, or Enterprise subscription) with agent mode available — see [`SETUP.md`](./SETUP.md) Step 1
- [ ] **Visual Studio Code** open in this repo's root folder
- [ ] **AI Dev Kit installed** and MCP server showing green — see [`SETUP.md`](./SETUP.md)
- [ ] **Formula 1 dataset cloned** into a `formula1-datasets/` folder in this repo — see [Get the Formula 1 data](#get-the-formula-1-data) below
- [ ] **Databricks workspace URL** on hand (format: `https://adb-XXXXXXX.azuredatabricks.net`)
  - Unity Catalog must be enabled
  - You need permission to create catalogs, schemas, SQL warehouses, and volumes
- [ ] **`databricks auth login`** completed — see [`SETUP.md`](./SETUP.md) Step 3

---

## Verify your MCP connection

Before running any prompts, confirm the Databricks MCP server is connected:

1. Open the Command Palette in VS Code: `Ctrl+Shift+P`
2. Search **"MCP: List Servers"**
3. Confirm `databricks` shows a **green** status indicator

If it's red, go back to [`SETUP.md`](./SETUP.md) — troubleshooting section.

---

## Get the Formula 1 data

The dataset is maintained upstream by [@toUpperCase78](https://github.com/toUpperCase78/formula1-datasets/tree/master) and is **updated frequently with new race results**, so you'll clone the latest copy rather than rely on a bundled snapshot.

From the repo root, in a **PowerShell** terminal:

```powershell
git clone https://github.com/toUpperCase78/formula1-datasets.git
```

This creates a `formula1-datasets/` folder containing the latest CSVs. Prompt 1 points Copilot at this folder by name.

> **Note:** Because you're pulling live data, exact row and file counts in this guide are approximate — the numbers will be a little higher than what's written here as more races are added each season. The data quality issues you'll fix (the two teaching moments) are structural and will still be present.

> **Already have the folder?** If a previous run left a `formula1-datasets/` folder behind, delete it first (`Remove-Item -Recurse -Force formula1-datasets`) so the clone pulls a clean, current copy.

---

## Prompt 1 — Data Profiling

Open **Copilot Chat** in VS Code (`Ctrl+Alt+I`), switch to **Agent mode**, and run this prompt. This step runs entirely locally — Copilot will generate and execute a Python script using pandas to profile the CSVs. No Databricks connection or MCP tools are needed.

```
Profile formula1-datasets before we plan the lakehouse. Do not load Spark or touch
Databricks — read the CSVs locally with pandas (nrows=5 is fine for shape; full read only
for row counts).

Produce a single DISCOVERY.md at the repo root with these sections, in this order:

1. File inventory — table of every CSV: filename, row count, column count, inferred family
   (race_results, qualifying, sprint_race, sprint_qualifying, calendar, drivers_season,
   teams_season, driver_of_day, videogame_ratings), year.
2. Filename collisions — any file whose name matches more than one plausible family regex.
   For each, list the columns and 2 sample rows so we can decide routing by content, not
   name. I specifically want to see formula1_2021season_sprintQualifyingResults.csv here.
3. Schema drift per family — for each family, a matrix of year × columns showing which
   columns appear in which year. Flag added/removed/renamed columns.
4. Join-key shape — for Driver, Team, Track (or their per-file equivalents): distinct count
   per year, plus 5 example values verbatim. Note any suffix patterns (e.g. Lewis Hamilton
   HAM).
5. Wide vs long — flag any file that's wide-format and will need unpivoting.
6. Surprises — bulleted list of anything that will force a design decision (missing columns,
   in-progress seasons with no driver/team snapshot, multiple snapshots per edition, encoding
   oddities, etc.).

Keep it under ~300 lines. No code blocks longer than 10 lines. No recommendations yet —
just observations. We'll enter plan mode after I read it.
```

### What Copilot will do

Copilot will write and run a local pandas script that reads all 50+ CSVs, classifies them into families, detects schema drift, and outputs a `DISCOVERY.md` file at the repo root. This typically takes 1–2 minutes.

### 🔍 Checkpoint — Review DISCOVERY.md

Open `DISCOVERY.md` in your editor and skim it:

- **File inventory** — confirm all CSVs are accounted for and family assignments look correct
- **Filename collisions** — check that `formula1_2021season_sprintQualifyingResults.csv` is flagged (sprint qualifying started in 2021 and the filename pattern overlaps with regular qualifying)
- **Schema drift** — note any columns that appear/disappear across years
- **Surprises** — these will inform the engineering ground rules in the next step

> **Why this step matters:** The profiling gives Copilot (and you) a concrete understanding of the data landscape before making any design decisions. It catches naming collisions, schema drift, and encoding issues up front — problems that would otherwise surface as silent failures during bronze ingestion.

---

## 🧠 Prompt Engineering Aside — Specification vs. Agency

The plan prompt in **Prompt 2** below is heavily *specified* — it carries six engineering ground rules. But that's not the only way to ask. Here are two versions of the same request. If you have time, **try both** (in separate fresh Copilot chats) and compare what the agent produces. There's no "correct" answer here — the point is to *feel* the tradeoff yourself.

**Version A — Lean (high agency)**

```
/plan please review the datasets available in the formula1-datasets folder and help me plan
how to migrate this to Databricks and unify the data in a medallion architecture. I have a
Databricks workspace created for when it gets to that. My thought is creating a unified data
model that has tables for drivers, races, teams, etc. Make sure to follow a snowflake schema
if possible.
```

**Version B — Guardrailed (high specification)** — the full six-rule prompt in Prompt 2 below.

### What you might observe

- **Version A** tends to be faster, the plan reads cleaner, and the agent leans on its own judgment — but defensive quality checks are sparser, so you rely more on the lab's UI checkpoints to catch issues.
- **Version B** encodes more data-engineering hygiene up front — but the rules are sometimes applied *less consistently* than you'd expect across a long build, and the agent occasionally adds defensive complexity it doesn't fully justify.

Neither outcome is a failure. They're two points on the same dial.

### Why this happens — in prompt-engineering terms

| Effect | What's going on |
| --- | --- |
| **Instruction dilution** | Every added constraint competes for the model's finite attention. Past a threshold it silently drops some — and you can't predict which. |
| **Attention decay** | A rule stated at the start of a 20-minute build is far out of context by the time the Gold layer is built, so it lands unevenly. |
| **Specification vs. agency** | Prescribing *how* can suppress the model's own good judgment and introduce implicit contradictions. |
| **Speculative complexity** | Abstract rules stated before the agent has seen a single join invite defensive code it applies mechanically rather than purposefully. |

> **The takeaway:** constraints aren't free. Add a rule only when it earns its place — and prefer phrasing it as a **verification assertion** ("assert every dim is unique on its key"), applied *at the phase where it matters*, over a design directive front-loaded into one mega-prompt. That's exactly why the six rules in Prompt 2 are written as checks rather than as instructions to "build it perfectly."

---

## Prompt 2 — Plan and build

Open a **new Copilot Chat** in VS Code (`Ctrl+Alt+I`), switch to **Agent mode**, and run this prompt:

```
Refer to DISCOVERY.md at the repo root for the full data profile of the formula1-datasets
folder.

/plan please review the datasets available in the formula1-datasets folder and help me plan
how to migrate this to Databricks and unify the data in a medallion architecture. I have a
Databricks workspace created for when it gets to that. My thought is creating a unified data
model that has tables for drivers, races, teams, etc. Make sure to follow a snowflake schema
if possible.

A few engineering ground rules for whatever you build:

1. Every dimension table must be unique on its surrogate key. End each dim with a
   dropDuplicates() on the key as defense-in-depth, and add a quality check that asserts
   the uniqueness for every dim.

2. Snowflaked parent dims must also be unique on the column the child joins by (not just
   on the surrogate key). If a child dim joins to a parent by name, the parent has to be
   one-row-per-name or the child will fan out.

3. When ingesting files into bronze, the file pattern must be specific enough that
   related-but-different file families don't leak into each other. Substring matches on
   things like "results" or "qualifying" are a common trap — prefer anchored patterns
   with explicit anti-matches for the families you don't want.

4. Any fact-to-dim join that depends on a time predicate (e.g., date-bounded versions of
   a dim) must put the time predicate inside the JOIN condition, not in a post-filter
   WHERE clause. A post-filter will silently drop fact rows that fall outside the dim's
   known time windows instead of leaving the dim key NULL.

5. Add a row-count parity check between silver and gold for any fact table that's a
   pass-through transformation. If gold ≠ silver, something fanned out or got dropped.

6. Add a small set of "known-truth" assertions to the quality checks — a handful of
   historical results that anyone can verify — so the job fails fast if a join silently
   inflates or deflates the data.

Build the plan in whatever order makes sense, but please honor those six rules throughout.
Walk me through the plan before you start executing.
```

> **Why the extra ground rules?** They're general data-engineering principles that catch the most common silent failure modes (fan-out, type-2 join drift, glob contamination) at build time instead of letting them surface as mysterious row-count mismatches three hours later. None of them give away the teaching moments — those still require you to look at the data and push back on the agent.

### What to do when the plan appears

Copilot will present a multi-step plan. **Review it, then approve it as written** — do not ask for modifications. Reply:

```
proceed!
```

> ⚠️ **Don't** ask Copilot to add additional profiling or remediation steps to the plan at this point. DISCOVERY.md already gave it the data landscape; the remaining data quality gaps are meant to surface naturally later in the lab — that's part of the exercise.

### What Copilot will do (this takes ~15–25 minutes)

Copilot will work through the phases automatically:

| Phase | What happens |
|---|---|
| Infrastructure | Creates `formula1` catalog, 4 schemas, UC volumes, SQL warehouse |
| Bronze ingestion | Uploads the CSVs → bronze Delta tables with schema merging + metadata |
| Team name lookup | Builds `silver.team_name_lookup` — resolves 70+ raw team name variants |
| Silver transform | Types, cleans, and normalises → 8 silver Delta tables |
| Gold layer | Builds 7 dimensions, 1 bridge table, 5 fact tables |
| Validation | Runs FK null checks, dim uniqueness assertions, silver↔gold parity, and known-truth checks |

You can follow along in the terminal. This is a good time to open **Databricks Catalog Explorer** in your browser and watch the catalog, schemas, and tables appear in real time.

### 🔍 UI Checkpoint — During Bronze / Silver phases

Once Copilot finishes Bronze ingestion, open **Databricks → Data → Catalog Explorer**:

1. Expand `formula1` → `bronze`
2. You should see 9 tables: `raw_race_results`, `raw_qualifying`, `raw_sprint`, etc.
3. Click any table → **Sample Data** tab → notice the `_source_file`, `_ingestion_timestamp`, `_season_year` metadata columns Copilot added automatically

---

## 🔎 Teaching Moment 1 — The team name problem (Phase 3)

After the silver layer team lookup is built, Copilot will log something like:

> *"Created `formula1.silver.team_name_lookup` — 70+ raw variants resolved to 18 canonical teams."*

Before Copilot continues to the full silver transform, open **Databricks → Data → Catalog Explorer**:

1. Navigate to `formula1` → `silver` → `team_name_lookup`
2. Click the **Sample Data** tab
3. Scroll through the entries — look at the `team_short_name` and `power_unit` columns

**Do any entries look suspicious?**

Look for team names that combine two different manufacturer names. Pay attention to rows where `power_unit` appears blank or odd.

<details>
<summary>💡 Hint (click to reveal)</summary>

Look for the entry `team_short_name = "Cadillac Ferrari"`. Is that a real F1 team? What should `team_short_name` and `power_unit` be separately?

</details>

### Your turn: craft the prompt

The agent hasn't caught this yet. What would you ask Copilot to do?

A good prompt should:
- **(a)** Name the suspicious entry so Copilot knows where to look
- **(b)** Ask Copilot to validate the **entire** lookup (not just fix the one entry it might already know)
- **(c)** Specify that it should use **public web sources** — not just guess

Try writing your own prompt before looking at the reference.

<details>
<summary>📋 Reference prompt (click to reveal)</summary>

```
The team_name_lookup has at least one suspicious entry — "Cadillac Ferrari" appears as a
team_short_name with no power_unit. That doesn't look right.

Please validate the complete team_name_lookup table against public web sources and fix any
misclassifications. Pay particular attention to entries where team_short_name combines two
manufacturer names, or where power_unit is blank.
```

</details>

### What Copilot will do

Copilot fetches Wikipedia pages for every ambiguous team entry and corrects the mappings. Key fixes it will find:

| Before | After |
|---|---|
| `team_short_name = "Cadillac Ferrari"`, no power unit | `team_short_name = "Cadillac"`, `power_unit = "Ferrari"` |
| `team_short_name = "Audi"`, no power unit | `team_short_name = "Audi"`, `power_unit = "Audi"` |
| Lotus mapped to wrong era teams | Corrected with year-specific engine suppliers |
| Caterham, Manor/Marussia ambiguities | Resolved via Wikipedia |

### 🔍 UI Checkpoint — After the fix

Refresh `formula1.silver.team_name_lookup` → Sample Data. Confirm:
- `Cadillac` now shows `power_unit = "Ferrari"`
- No `team_short_name` values combine two manufacturer names
- No blank `power_unit` entries

> **Why this matters:** Every downstream silver and gold table joins through this lookup. If `Cadillac Ferrari` stayed wrong, constructor win counts and team aggregations would be off — and it would show up in the dashboard you build later.

---

## Back to the build — Silver and Gold phases

Tell Copilot to continue:

```
continue
```

Copilot will run through the silver transformation (Phase 4) and full gold layer (Phase 5). This takes another 10–15 minutes.

### 🔍 UI Checkpoint — After Gold builds

Open **Catalog Explorer** → `formula1` → `gold`:

1. Open `dim_drivers` → **Sample Data** — clean typed data: `date_of_birth` as a date, stats as integers
2. Open `dim_teams` → **Sample Data** — verify no `power_unit` nulls (the fix from Teaching Moment 1 flows all the way here)
3. Open `fact_race_results` → **Sample Data** — `grid_position`, `finish_position` as integers, `race_time_seconds` as a float

---

## 🔎 Teaching Moment 2 — The calendar gap (Phase 6 validation)

When the Gold layer finishes, Copilot will run validation and report something like:

> *"`fact_race_results.round_key`: NULL for 2,971 of 5,609 rows (~53%). Expected — calendar CSVs only cover 2019–2026."*

It may then move on to the next step or wrap up.

**Stop.** Don't let this slide.

Open **Databricks → SQL Editor** (or use Catalog Explorer's query tab) and run:

```sql
SELECT COUNT(*) AS null_round_keys
FROM formula1.gold.fact_race_results
WHERE round_key IS NULL;
```

You should see roughly **half** of all race results have no link to a calendar round — about 2,000–3,000 rows depending on how much current-season data you cloned.

Also run:

```sql
SELECT season, COUNT(*) AS races, SUM(CASE WHEN round_key IS NULL THEN 1 ELSE 0 END) AS missing_round_key
FROM formula1.gold.fact_race_results
GROUP BY season
ORDER BY season;
```

You'll see that **all seasons with null round_keys are 2013–2018** — the calendar CSVs in this repo only cover 2019 onwards.

The agent classified this as "expected — source data gap." **Is that acceptable?** Half your race results have no link to a round, season, or circuit in the dimensional model. Joins to `dim_race_rounds`, `dim_circuits`, and `dim_seasons` won't work for 6 years of races.

### Your turn: craft the prompt

What would you ask Copilot to do?

A good prompt should:
- **(a)** Push back on accepting the gap rather than just reporting it
- **(b)** Direct Copilot to a public source for historical F1 calendar data (hint: there's a free API at `api.jolpi.ca/ergast/f1/{year}/races.json` — no auth required)
- **(c)** Give a clear success criterion (e.g., "0 null round_keys")
- **(d)** Ask Copilot to look for and fix any data quality issues in silver that would prevent clean joins

Try writing your own before looking at the reference.

<details>
<summary>📋 Reference prompt — Prompt 4 (click to reveal)</summary>

```
Validation showed that fact_race_results has null round_key for ~50% of rows because
calendar CSVs only cover 2019–2026. I'd like to fix this rather than accept it.

Please:
1. Diagnose the exact scope — how many rows have null round_key, and which seasons/circuits
   are missing from dim_race_rounds.
2. Use the Jolpica API (api.jolpi.ca/ergast/f1/{year}/races.json) to fetch the 2013–2018
   season calendars. It's free, no authentication needed.
3. Identify and fix any data quality issues in silver.race_results that would prevent
   correct joins (mismatched circuit names, typos, etc.).
4. Add any missing circuits to dim_circuits (circuits that only existed pre-2019).
5. Insert new rows into dim_race_rounds for all 6 missing seasons.
6. Rebuild the affected fact_race_results rows so round_key is 100% populated.
7. Validate by checking that known champions' win counts match historical records.
```

</details>

### What Copilot will do

Copilot will:
1. Query `silver.race_results` to find the exact missing circuit names
2. Fetch 6 seasons of calendar data from `api.jolpi.ca` (119 races, 2013–2018)
3. Find and fix source data quality issues — typos like `"Sinagpore"`, `"Great Brtiain"` in the silver data
4. Add 3 retired circuits to `dim_circuits` (Korean, Indian, Malaysian)
5. Insert 119 new rows into `dim_race_rounds`
6. Rebuild `fact_race_results` rows with correct `round_key` values
7. Validate against known champion win counts (Vettel 2013, Hamilton 2014, etc.)

### 🔍 UI Checkpoint — After the fix

Re-run your two validation queries in the SQL Editor:

```sql
-- Should return 0
SELECT COUNT(*) FROM formula1.gold.fact_race_results WHERE round_key IS NULL;

-- Should show data for all 14 seasons
SELECT season, COUNT(*) AS races
FROM formula1.gold.fact_race_results
GROUP BY season ORDER BY season;
```

Nulls drop to **0**. All seasons are now fully joined to the dimensional model.

> **Why this matters:** This is the most compelling pattern in the whole lab. Copilot fetched a public API, diagnosed data quality issues it found along the way, and rebuilt the fact table to be 100% FK-complete — all from a single prompt. No manual download, no spreadsheet work.

---

## Prompt 3 — Build the dashboard

Now the data is clean. Let's make it visible.

Run this prompt:

```
Now create a Databricks AI/BI dashboard to showcase the cleaned data. Include:
- Constructor wins by season (stacked bar, 2013–2026)
- Driver wins by season (stacked bar, 2013–2026)
- All-time driver wins top 15 (bar chart)
- Constructor championship points by season (stacked bar)

Before building, search GitHub for real Databricks .lvdash.json examples (e.g., in the
databricks/tmm repo) to confirm the correct widget JSON structure — especially how fields,
encodings, and the disaggregated flag work for bar charts.
```

### 🔍 UI Checkpoint — Live dashboard

Open **Databricks → Dashboards** in the left nav. You should see **"Formula 1 Championship Analysis"**.

Open it. All four chart widgets should render data:

- **Constructor Wins by Season** — look at the team names in the legend. They're clean: `Red Bull Racing`, `Mercedes`, `McLaren` — no `"McLaren Mercedes"` or `"Red Bull Racing Honda RBPT"` noise. That's Teaching Moment 1 paying off.
- **Driver Wins by Season** — Vettel era (2013–2014), Hamilton era (2015–2020), Verstappen era (2021–2026). All 14 seasons visible because of Teaching Moment 2.
- **All-Time Driver Wins (Top 15)** — Hamilton leads, Verstappen second. The counts are accurate because `fact_race_results` is now 100% FK-complete.

---

## Teardown

When you're done, clean up the workspace to avoid unnecessary spend.

Run this prompt:

```
Please drop the formula1 catalog and all its contents, and stop the formula1-warehouse.
```

Copilot will ask you to confirm before dropping the catalog (destructive operation). Confirm, then verify in **Catalog Explorer** that `formula1` no longer appears.

---

## Stuck or curious?

Compare the `lab` branch to `main` to see exactly what Copilot generated:

```powershell
git diff main lab -- notebooks/
```

Or browse the `main` branch on GitHub and read [`SOLUTION.md`](https://github.com/MaxBush6299/ghcp-databricks-de-lab/blob/main/SOLUTION.md) for the full phase-by-phase narrative with Copilot callouts.
