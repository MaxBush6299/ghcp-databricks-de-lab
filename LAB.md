# Lab: Automated Data Engineering with GitHub Copilot CLI + Databricks

> **You are on the `lab` branch.** The completed reference (generated notebooks + full walkthrough) lives on [`main`](../../tree/main).

---

## What you'll build

A **Formula 1 medallion lakehouse** in Databricks — entirely through conversation with GitHub Copilot CLI.

Starting from 60 raw CSV files across 14 seasons, you'll end up with:

- A Unity Catalog hierarchy: `formula1.{raw, bronze, silver, gold}`
- 9 Bronze Delta tables with schema-merged, metadata-enriched ingestion
- 8 Silver tables with proper types, deduplication, and normalised team names
- A full **snowflake dimensional model** in Gold (7 dimensions, 1 bridge, 5 facts)
- A live **AI/BI dashboard** — Constructor wins, Driver wins, all-time leaderboards

You'll also discover two real data quality issues mid-lab and craft the prompts to fix them yourself — that's the point.

**Estimated time:** 60–90 minutes (most of it is watching Copilot work).

---

## Prerequisites checklist

Before you start, confirm:

- [ ] **GitHub Copilot CLI** installed and signed in to your GitHub account (Copilot licence required)
- [ ] **Visual Studio Code** open in this repo's root folder
- [ ] **AI Dev Kit installed** and MCP server showing green — see [`SETUP.md`](./SETUP.md)
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

## Prompt 1 — Plan and build

Open a Copilot CLI session in the VS Code terminal and run this prompt:

```
/plan please review the datasets available in the formula1-datasets folder and help me plan
how to migrate this to Databricks and unify the data in a medallion architecture. I have a
Databricks workspace created for when it gets to that. My thought is creating a unified data
model that has tables for drivers, races, teams, etc. Make sure to follow a snowflake schema
if possible.
```

### What to do when the plan appears

Copilot will present a multi-step plan. **Review it, then approve it as written** — do not ask for modifications. Reply:

```
proceed!
```

> ⚠️ **Don't** ask Copilot to add profiling or remediation steps to the plan at this point. The data quality gaps are meant to surface naturally later in the lab — that's part of the exercise.

### What Copilot will do (this takes ~15–25 minutes)

Copilot will work through the phases automatically:

| Phase | What happens |
|---|---|
| Infrastructure | Creates `formula1` catalog, 4 schemas, UC volumes, SQL warehouse |
| Bronze ingestion | Uploads 60 CSVs → 9 bronze Delta tables with schema merging + metadata |
| Team name lookup | Builds `silver.team_name_lookup` — resolves 70+ raw team name variants |
| Silver transform | Types, cleans, and normalises → 8 silver Delta tables |
| Gold layer | Builds 7 dimensions, 1 bridge table, 5 fact tables |
| Validation | Runs FK null checks and row count reconciliation |

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

You should see approximately **2,971 rows** with no link to a calendar round — about half of all race results.

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
<summary>📋 Reference prompt — Prompt 3 (click to reveal)</summary>

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

Nulls drop from **2,971 → 0**. All 14 seasons are now fully joined to the dimensional model.

> **Why this matters:** This is the most compelling pattern in the whole lab. Copilot fetched a public API, diagnosed data quality issues it found along the way, and rebuilt the fact table to be 100% FK-complete — all from a single prompt. No manual download, no spreadsheet work.

---

## Prompt 2 — Build the dashboard

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

Or browse the `main` branch on GitHub and read [`SOLUTION.md`](../../blob/main/SOLUTION.md) for the full phase-by-phase narrative with Copilot callouts.
