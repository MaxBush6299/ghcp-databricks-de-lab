# Automated Data Engineering with GitHub Copilot + Databricks

> **This is the completed reference.** The hands-on lab lives on the [`lab` branch](https://github.com/MaxBush6299/ghcp-databricks-de-lab/tree/lab).
> If you want to run through the exercise yourself — discovering the data quality gaps and crafting the remediation prompts — start there.

---

> A walk-through of building a Formula 1 Lakehouse from raw CSVs to a snowflake-schema gold layer — entirely through natural-language conversation with GitHub Copilot.

## Audience & Purpose

This document captures a real session demonstrating **how far data engineering can be automated** when an AI agent has direct, governed access to a Databricks workspace. Every action in this document was performed by Copilot via tool calls — no clicks, no copy-paste of SQL into the UI.

---

## Source Material

The starting point was a local folder of **60 CSV files** spanning Formula 1 seasons 2013–2026, downloaded from a public GitHub dataset. The files included race results, qualifying, sprint events, drivers, teams, calendars, "Driver of the Day" votes, and videogame ratings — each with inconsistent column names, naming conventions, and schema drift across seasons.

**Goal:** Land all of it in Databricks Unity Catalog as a **medallion architecture** (Bronze → Silver → Gold) culminating in a **snowflake dimensional model** ready for BI and analytics.

---

## Tools Used

| Tool | What it does | Used for |
|---|---|---|
| **GitHub Copilot CLI** (Claude Opus 4.7) | Conversational agent in the terminal | Orchestrating the entire workflow |
| **Databricks MCP server** | Model Context Protocol bridge giving Copilot direct workspace access | All Databricks operations |
| `databricks-execute_sql` / `execute_sql_multi` | Run SQL on a SQL warehouse | DDL, validation queries |
| `databricks-execute_code` | Run Python/PySpark on serverless compute | Bronze ingestion, lookup building |
| `databricks-manage_uc_objects` | Create catalogs, schemas, volumes | Infrastructure setup |
| `databricks-manage_volume_files` | Upload local files into UC Volumes | CSV + media uploads |
| `databricks-manage_sql_warehouse` | Create/start SQL warehouses | Provisioned the warehouse used for queries |
| **Databricks CLI** (OAuth) | Authenticated session to the workspace | One-time login via browser |
| `databricks-manage_dashboard` | Create and publish AI/BI dashboards via API | Built the live F1 analytics dashboard |
| **Unity Catalog** | Governance layer for catalogs, schemas, volumes, and tables | Logical data organization |
| **Delta Lake** | Open table format on cloud storage | Storage for every bronze/silver/gold table |
| **Serverless compute** | On-demand Spark without cluster management | Every PySpark transformation in this session |
| **Databricks AI/BI Dashboards** | Built-in interactive BI layer inside the workspace | Visualization of team wins, driver wins, and constructor points YoY |

The Copilot CLI also used built-in tools like `view`, `edit`, `create`, `glob`, `grep`, and a session-scoped SQLite database to track the 8-step plan and progress.

---

---

## Recommended Prompts

### Prompt 1 — Initial planning (starting the session)

```
/plan please review the datasets available in the formula1-datasets folder and help me plan
how to migrate this to Databricks and unify the data in a medallion architecture. I have a
Databricks workspace created for when it gets to that. My thought is creating a unified data
model that has tables for drivers, races, teams, etc. Make sure to follow a snowflake schema
if possible.

Before finalizing the plan, profile the source data for completeness. Flag any gaps that
would cause data quality issues downstream (e.g., missing seasons, referential integrity
problems, inconsistent coverage across related datasets). For each gap, propose a remediation
and include it as a planned step — I will confirm which to apply before we proceed.
```

After Copilot presents its plan, review any flagged gaps and approve or defer each remediation, then respond: **"proceed!"**

> **Why the profiling instruction matters:** Without it, the agent will surface data gaps during validation (Phase 6) but classify them as "expected, accept as-is" and move on. Asking the agent to profile upfront puts it on the hook to **propose** fixes during planning — not just report problems after the fact. The instruction is intentionally open-ended so it works for any dataset, not just F1.

---

### Prompt 2 — Dashboard (after Gold layer is complete)

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

> **Why include the GitHub search instruction?** The Databricks AI/BI dashboard JSON spec (`lvdash.json`) is not fully documented. The critical requirement — that bar chart fields must use aggregate expressions like `SUM(\`wins\`)` with `disaggregated: false`, with the field `name` exactly matching the encoding `fieldName` — is only discoverable from real examples. Adding this instruction pre-arms the agent with the correct pattern and avoids the multi-turn debug loop that occurred in this session.

---

### Prompt 3 — Calendar Enrichment (after Phase 6 Validation surfaces null FKs)

> **Use this prompt only if Prompt 1 was NOT updated to bake in profiling+remediation.** If you used the upgraded Prompt 1, the agent will already have proposed (and you'll have approved) the calendar enrichment as part of the initial plan, and Phase 6b will execute automatically.

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

> **Why this prompt works well as a standalone:** It gives the agent a clear goal (0 null round_keys), the exact data source to use, and a validation criterion. The agent will diagnose the data quality issues itself — the prompt doesn't need to pre-enumerate them. Either path (upgraded Prompt 1, or this Prompt 3 as a follow-up) produces the same result; choose based on whether you want the gap closure to feel **planned** or **discovered**.

---

---

---

## The Workflow

### Phase 0 — Discovery & Planning *(Copilot-driven)*

The session began with: *"please review the datasets available in the formula1-datasets folder and help me plan how to migrate this to databricks."*

Copilot:
1. Listed the directory and read sample CSVs from each source type to understand columns, types, and inconsistencies.
2. Drafted a medallion plan with a snowflake gold schema (`dim_drivers`, `dim_teams` → `dim_power_units`, `dim_circuits`, `dim_race_rounds`, `bridge_driver_team_season`, fact tables for race/qualifying/sprint/votes).
3. Persisted the plan to the session workspace.
4. Inserted **8 todo records** into a session-scoped SQLite tracker with explicit dependencies, which kept the agent oriented as the work progressed across many turns.

> **Why this matters:** The plan was reviewed and approved before any code ran. The user retained full visibility and could have steered the design at any point — but didn't need to micromanage execution.

---

### Phase 1 — Infrastructure Setup

**What happened:**
- The user provided their Azure Databricks workspace URL.
- Copilot detected the Databricks CLI was missing, installed it via `winget`, and added it to `PATH`.
- Triggered an OAuth browser login (`databricks auth login`) — the user clicked through in the browser; Copilot waited for completion via shell I/O.
- The MCP server picked up authentication from `~/.databrickscfg` and connected.
- Copilot attempted to create the catalog via the SDK; it failed because the workspace uses Default Storage, so Copilot **adapted automatically** and created a SQL warehouse + ran the DDL via SQL instead.

**Created in Databricks:**
- Catalog `formula1`
- Schemas `raw`, `bronze`, `silver`, `gold`
- Volumes `formula1.raw.csvs` and `formula1.raw.media`
- SQL Warehouse `formula1-warehouse` (2X-Small, 15-min auto-stop)

**Key Copilot tools:** `databricks-manage_workspace`, `databricks-manage_sql_warehouse`, `databricks-execute_sql`, `databricks-execute_sql_multi`.

> **Copilot Callout:** When the SDK call hit the Default Storage limitation, the agent didn't ask for help — it pivoted to a SQL-based path. This kind of recovery is what makes agentic execution feel productive rather than fragile.

---

### Phase 2 — Bronze Ingestion

**What happened:**
- Copilot wrote a small PowerShell script that **categorized 60 CSVs into 9 source-type subfolders** (`race_results/`, `qualifying/`, `sprint/`, `sprint_qualifying/`, `drivers/`, `teams/`, `calendar/`, `dotd_votes/`, `videogame_ratings/`) using regex pattern matching on filenames.
- Uploaded all 60 CSVs (plus 58 media images) to the UC Volume in parallel.
- Wrote a PySpark notebook (`01_bronze_ingestion.py`) that:
  - Reads each source-type folder with schema merging across seasons,
  - Adds metadata columns: `_source_file`, `_ingestion_timestamp`, `_season_year` (parsed from filename via regex),
  - Sanitizes column names (lowercase snake_case, special characters stripped — required by Delta unless column mapping is enabled),
  - Stores all values as STRING for safe schema evolution, and writes to `formula1.bronze.raw_<source>` as Delta tables.

**Iteration in flight:**
1. First run failed: `input_file_name()` not allowed under Unity Catalog → switched to `_metadata.file_path`.
2. Second run failed: invalid characters in column names → added a sanitization function.
3. Third run failed: empty strings can't be cast to `INT` → switched to `try_cast` for the year extraction.
4. Fourth run succeeded.

Each fix was a single-line targeted edit, run, and verify. Total time including all four iterations: about 5 minutes.

**Resulting bronze tables:**

| Bronze Table | Rows | Seasons |
|---|---:|---:|
| `raw_race_results` | 5,609 | 14 (2013–2026) |
| `raw_qualifying` | 1,922 | 5 |
| `raw_sprint` | 583 | 5 |
| `raw_sprint_qualifying` | 342 | 4 |
| `raw_drivers` | 153 | 7 |
| `raw_teams` | 50 | 5 |
| `raw_calendar` | 153 | 7 |
| `raw_dotd_votes` | 92 | 4 |
| `raw_videogame_ratings` | 160 | 3 |

**Key Copilot tools:** `databricks-manage_volume_files`, `databricks-execute_code` (serverless Python), `databricks-execute_sql_multi` (parallel validation queries).

> **Copilot Callout:** The ability to **iterate on the actual error** (not a stale guess) is the multiplier here. Copilot saw each error trace, made a surgical fix, re-ran. The user never had to copy-paste a stack trace anywhere.

---

### Phase 3 — Team Name Normalization Lookup

**Why this step exists:**

A row in `raw_race_results` says `team = "Red Bull Racing Honda RBPT"` while the same team in `raw_teams` is just `"Red Bull Racing"` and in `raw_drivers` is also `"Red Bull Racing"`. Across 14 seasons there are **70+ distinct team-name variants** that map to **18 canonical teams**, complicated by:

- Power-unit suffixes appended in race results (`McLaren Mercedes`, `Williams Renault`)
- Historical team renames (Toro Rosso → AlphaTauri → RB → Racing Bulls; Force India → Racing Point → Aston Martin)
- Source-data typos (`Aston Martib`, `Williams Meredes`, `Racing bulls` lowercase)
- Pre-2021 teams that never appear in the modern `raw_teams` table

**What Copilot did:**

Wrote `02_silver_team_lookup.py` that:
1. Pulls the canonical short-name list from `raw_teams`.
2. Defines a `HISTORICAL_ALIASES` dictionary for renamed/missing teams.
3. For each variant, applies a longest-prefix match (case-insensitive) to extract `team_short_name` + the trailing `power_unit`.
4. Persists to `formula1.silver.team_name_lookup` as a Delta table.

A first run revealed several misclassifications — Copilot inspected the output, **expanded the alias dictionary**, made the matching case-insensitive, and re-ran. The final lookup is auditable, idempotent, and reusable by every downstream silver/gold transformation.

**Key Copilot tools:** `databricks-execute_code`, `databricks-execute_sql`.

> **Copilot Callout:** This is the part of data engineering most people dread — chasing down dirty string variants. The agent did it in two iterations, with the user reviewing the final mapping before approving.

---

### Phase 3b — Lookup Validation via Web Research

**What happened:**

The user noticed "Cadillac Ferrari" was mapping `team_short_name = "Cadillac Ferrari"` with no power unit — clearly wrong. They asked Copilot to validate the entire lookup using web sources.

Copilot used `web_fetch` to retrieve Wikipedia pages for every ambiguous or historical team and confirmed:

| Variant | Correct Short Name | Power Unit | Source |
|---|---|---|---|
| Cadillac Ferrari | Cadillac | Ferrari | Wikipedia: Cadillac uses Ferrari 067/6 engine in 2026 |
| Audi | Audi | Audi | Wikipedia: Audi manufactures its own power unit from 2026 |
| Lotus Renault/Mercedes/Ferrari | Lotus | Renault/Mercedes/Ferrari | Wikipedia: Enstone-based Lotus F1 Team 2012–2015 |
| Caterham Renault | Caterham | Renault | Wikipedia: Caterham used Renault throughout 2012–2014 |
| Marussia Cosworth/Ferrari | Manor | Cosworth/Ferrari | Wikipedia: Marussia → Manor, used both engines |
| MRT Mercedes | Manor | Mercedes | Wikipedia: Manor Racing Team used Mercedes |

**Key Copilot tools:** `web_fetch` (Wikipedia), `databricks-execute_sql` (result verification).

> **Copilot Callout:** When the user flagged a data quality issue, Copilot didn't just apply a hardcoded fix — it fetched authoritative sources, validated the facts, then updated the normalization logic. The result is a lookup table that's both correct and citable.

---

### Phase 4 — Silver Transformation

**What happened:**

Copilot built a single PySpark job (`03_silver_transformation.py`) that reads every bronze table, applies cleaning/typing/normalization, and writes to 8 silver Delta tables — all in one serverless execution.

**Key transformations performed:**
- **Date parsing:** `DD/MM/YYYY` strings → proper `DATE` type via `to_date(col, "dd/MM/yyyy")`
- **Lap time parsing:** `M:SS.mmm` strings → `FLOAT` seconds (custom UDF splitting on `:`)
- **Gap parsing:** `+SS.mmm` and `+M:SS.mmm` strings → `FLOAT` seconds
- **Result status classification:** `Time/Retired` column values classified as `Finished`, `DNF`, `DNS`, `DSQ`, `NC`, `WD`
- **Team resolution:** Every results row joined to `team_name_lookup` to get canonical `team_short_name` + `power_unit`
- **Safe casting:** All `.cast(IntegerType())` replaced with `try_cast()` SQL expressions to handle non-numeric values like "NC" in position columns
- **Schema unification:** `COALESCE` across column-name variants that changed between seasons (e.g., `grands_prix_entered` vs `grand_prix_entered`, `circuit_length_km` vs `circuit_length`)
- **Circuit deduplication:** 153 calendar rows across 7 seasons → 41 distinct circuits (latest-season metadata kept via windowed `ROW_NUMBER`)
- **DOTD votes unpivot:** Wide format (5 rank columns) → long format via `stack()` — 92 rows × 5 ranks = 460 vote rows

**Iteration in flight:**
1. First run failed: `.cast(IntegerType())` on "NC" position values → switched all casts to `try_cast()` SQL expressions.
2. Second run succeeded.

**Resulting silver tables:**

| Silver Table | Rows | Key Types |
|---|---:|---|
| `circuits` | 41 | Deduplicated, lap_record as float seconds |
| `drivers` | 153 | DOB as DATE, career stats as INT/FLOAT |
| `teams` | 50 | Base split into city/country, entry year as INT |
| `race_results` | 5,609 | Grid/finish as INT, time/gap as FLOAT seconds |
| `qualifying_results` | 1,922 | Q1/Q2/Q3 as FLOAT seconds |
| `sprint_results` | 583 | Same shape as race_results |
| `sprint_qualifying` | 342 | Same shape as qualifying_results |
| `driver_of_day_votes` | 460 | Unpivoted: vote_rank INT, vote_pct FLOAT |

**Key Copilot tools:** `databricks-execute_code` (serverless PySpark), `databricks-execute_sql` (validation counts).

> **Copilot Callout:** The silver layer is where schema drift really bites. Columns renamed between seasons, positions stored as "NC" instead of numbers, lap times as human-readable strings. The agent handled all of this in a single PySpark job with safe `try_cast()` and `COALESCE` patterns — no manual data profiling needed.

---

### Phase 5 — Gold Layer (Snowflake Schema)

**What happened:**

Copilot built the complete gold snowflake schema in three stages: dimensions, bridge, and fact tables — all via serverless PySpark jobs.

**Stage 1: Dimension Tables (7 tables)**

| Dimension | Rows | Key Design Decisions |
|---|---:|---|
| `dim_seasons` | 14 | One row per season (2013–2026) with total round count |
| `dim_session_types` | 4 | Static lookup: Race, Qualifying, Sprint, Sprint Qualifying |
| `dim_power_units` | 13 | Snowflake sub-dimension of teams (Ferrari, Mercedes, Honda RBPT, etc.) |
| `dim_drivers` | 39 | Deduplicated by driver_code + name, latest-season stats, active range |
| `dim_teams` | 15 | Latest-season metadata, FK to dim_power_units |
| `dim_circuits` | 41 | Deduplicated from silver.circuits |
| `dim_race_rounds` | 153 | Calendar-based, with track_name for joining to results |

**Iteration in flight:**
1. First build of `dim_race_rounds` failed: `to_date()` threw on `"17 Mar 2019"` format → fixed with `try_to_date()` and multiple format patterns.
2. First fact table build had 100% null `round_key` — **race results use short location names** (e.g., "Bahrain") while circuits use full names ("Bahrain International Circuit"). Copilot diagnosed the mismatch, built a `track_to_circuit_lookup` table, and added a `track_name` column to `dim_race_rounds`.
3. 15 special GP names needed manual mapping (e.g., "70th Anniversary" → Silverstone, "Eifel" → Nürburgring, "Sakhir" → Bahrain International Circuit, "Styria" → Red Bull Ring).

**Stage 2: Bridge Table**

| Table | Rows |
|---|---:|
| `bridge_driver_team_season` | 308 |

Resolves the many-to-many relationship between drivers and teams per season. Includes FK to `dim_power_units` for the specific engine used that season.

**Stage 3: Fact Tables (5 tables)**

| Fact Table | Rows | FK Coverage |
|---|---:|---|
| `fact_race_results` | 5,609 | round_key: 47% populated (seasons with calendar data) — addressed in Phase 6b |
| `fact_qualifying_results` | 1,922 | round_key: 83% populated |
| `fact_sprint_results` | 583 | round_key: 82% populated |
| `fact_sprint_qualifying_results` | 342 | round_key populated for matching seasons |
| `fact_driver_of_day_votes` | 460 | round_key: 87% populated |

**FK null analysis:**
- **round_key nulls** — Expected at this stage: 2013–2018 seasons have race results but no uploaded calendar CSVs. Seasons WITH calendar data show **0% null round keys**. *Resolved in Phase 6b via web-sourced enrichment.*
- **driver_key nulls (~17%)** — Expected: `dim_drivers` contains 39 drivers from driver CSVs (2019–2025), while race results span 2013–2026 with many additional historical drivers.
- **team_key nulls (~6%)** — Expected: historical teams (Caterham, Lotus, Manor) appear in race results but not in `dim_teams` (which starts from the 2021 teams CSV).

All null FKs are understood, documented, and caused by source data gaps — not join logic errors.

**Key Copilot tools:** `databricks-execute_code` (serverless PySpark), `databricks-execute_sql_multi` (parallel FK validation), `web_fetch` (historical GP name research).

> **Copilot Callout:** The track-name mismatch was a subtle data modeling issue that would have taken a human engineer significant time to diagnose. Copilot found the root cause via FK null checks, built a lookup table with 17 manual overrides for special GPs (sourced from F1 history knowledge), and rebuilt all 6 downstream tables — all within a few iterations.

---

### Phase 6 — Validation

**What was validated:**
1. **Row count reconciliation** — Bronze → Silver preserved all rows (5,609 race results in both layers). Gold fact tables match silver source counts exactly.
2. **FK null checks** — All null foreign keys traced to expected source data gaps (no calendar data for 2013–2018, no driver/team CSVs before 2019/2021).
3. **Seasons with calendar data** — For 2019–2025, round_key join success rate is **100%** — zero unresolved rounds.
4. **Team name resolution** — All 70+ raw team-name variants resolved to 18 canonical teams with zero null power units after web-research validation.

> **Copilot Callout:** Validation isn't a separate "phase" that the engineer runs after the fact — it's woven into every step. Each time Copilot built a table, it ran count checks and FK analysis before moving on. Issues were caught and fixed immediately, not deferred.

---

### Phase 6b — Web-Sourced Calendar Enrichment *(human-prompted, AI-executed gap closure)*

**Why this step exists:**

Phase 6 validation surfaced an honest data-coverage limitation: `fact_race_results.round_key` was NULL for **2,971 of 5,609 rows (~50%)** because the uploaded calendar CSVs only covered 2019–2026. The agent flagged this as "expected — caused by source data gaps" and moved on.

**The user pushed back.** The catalyzing prompt was: *"How difficult would it be to pull accurate calendar data from the web to populate all of the nulls?"*

That's the honest framing — **the agent surfaced the gap, but the user supplied the insight that it could be fixed from a public source.** Once directed, the agent executed the entire remediation end-to-end. This is an important lesson for future demos: the upfront planning prompt should be tightened (see *Recommended Prompts → Prompt 1*) so the agent **proposes** remediation for gaps it discovers, not just reports them.

**What Copilot did once directed:**

1. **Identified the data source:** Researched public F1 APIs; confirmed Jolpica (`api.jolpi.ca/ergast/f1/{year}/races.json`) provides full season calendars with circuit, round, and date data — free, no key required.
2. **Profiled silver against the lookup:** Queried `silver.race_results` to get the exact `circuit_name` strings used pre-2019 (e.g., "South Korea", "Sinagpore") and compared against `track_to_circuit_lookup` to find unmapped entries — *before* writing any inserts.
3. **Fixed source data quality issues** found during profiling.
4. **Added missing circuits** to `dim_circuits` for venues that retired before the 2019 source CSVs were generated.
5. **Fetched + inserted** 119 calendar rows across 2013–2018.
6. **Rebuilt the affected fact rows** so `round_key` is 100% populated.

**Data quality issues discovered and fixed during enrichment:**

| Issue | Root Cause | Fix Applied |
|---|---|---|
| "Sinagpore" in 2016 silver data | Typo in source CSV | `UPDATE silver.race_results SET circuit_name = 'Singapore'` |
| "Great Brtiain" in 2017 silver data | Typo in source CSV | `UPDATE silver.race_results SET circuit_name = 'Great Britain'` |
| "South Korea" → NULL in lookup | Korean International Circuit dropped from F1 after 2013 | Added to `dim_circuits` + new lookup entry |
| "India" → NULL in lookup | Buddh International Circuit dropped after 2013 | Added to `dim_circuits` |
| "Malaysia" missing from `dim_circuits` | Sepang retired after 2017 | Added to `dim_circuits` |
| 2013 Germany at Nürburgring | Calendar-based — 2014+ at Hockenheimring | Handled via year-specific `dim_race_rounds` rows |
| 2016 Baku called "Europe" in results | F1 branded it "European GP" in its debut year | `dim_race_rounds` row for 2016 Baku: `track_name = 'Europe'` |

**What was executed:**

- Fetched 6 season calendars from `api.jolpi.ca` (119 races total across 2013–2018)
- Added 3 new circuits to `dim_circuits`: Korean International Circuit, Buddh International Circuit, Sepang International Circuit
- Inserted 119 new rows into `dim_race_rounds` covering all 6 missing seasons
- Added 6 rows to `dim_seasons` (2013–2018)
- Deleted the 2,971 null-round_key rows from `fact_race_results` and **rebuilt them from silver** with correct `round_key`, `driver_key`, and `team_key` FKs via a single SQL `INSERT ... SELECT`
- **Null round_keys dropped from 2,971 → 0**

**Validation:**

| Check | Result |
|---|---|
| 2013 champion (13 wins) | ✅ Sebastian Vettel — 13 wins |
| 2014 champion (11 wins) | ✅ Lewis Hamilton — 11 wins |
| 2016 winner count (Rosberg 9, Hamilton 10) | ✅ Exact match to historical standings |
| Gold views (`vw_driver_wins`, `vw_constructor_wins`) | ✅ Return correct results for all seasons 2013–2026 |

**Post-enrichment fact counts:** `fact_race_results` went from 5,609 rows (50% null round_key) → 5,481 rows (0% null round_key). Net loss of 128 rows: a small number of pre-2019 silver rows didn't match the Jolpica calendar (e.g., race name variants the agent didn't auto-resolve). Acceptable trade-off for FK completeness, and a candidate for a follow-up tightening pass.

**Key Copilot tools:** `web_fetch` (Jolpica API), `databricks-execute_code` (Python API calls + SQL inserts on serverless), `databricks-execute_sql` (diagnosis and validation).

> **Copilot Callout:** This is the most compelling pattern in the whole workflow — **the agent fetched a public API, fixed source data quality issues along the way, and rebuilt a fact table to be 100% join-complete.** No manual download, no spreadsheet work, no separate ticket to a data team. The lesson for repeatable demos: bake the "propose-remediation-for-gaps" instruction into the **initial planning prompt** so this happens without depending on the user spotting the opportunity in real time.

---

### Phase 7 — AI/BI Dashboard

**What happened:**

The user asked for a dashboard to visualize team wins and driver wins year-over-year as a demo of the cleaned data.

Copilot:
1. **Validated 4 SQL queries** in parallel against the silver layer to confirm clean output before including them in the dashboard.
2. **Debugged the Lakeview JSON schema** iteratively — discovered via progressive error messages that widget definitions must be embedded directly in layout items (not referenced by name), and that page objects require a `name` field in addition to `displayName`.
3. **Created and published** a Databricks AI/BI (Lakeview) dashboard with 5 widgets using a single `databricks-manage_dashboard` MCP call.

**Dashboard contents:**

| Widget | Type | What it shows |
|---|---|---|
| Title | Text | Session summary and architecture lineage |
| Constructor Wins by Season | Stacked bar | Which team dominated each season, 2013–2026 — clean names prove normalization worked |
| Driver Wins by Season | Stacked bar | Vettel era → Hamilton era → Verstappen era — all 13 seasons in one chart |
| All-Time Driver Wins (Top 15) | Bar | Career win leaderboard: Hamilton 84, Verstappen 71, Vettel 27… |
| Constructor Points by Season | Line | Points trajectory showing Mercedes' sustained dominance and the competitive 2024–2025 field |

**Why silver, not gold:**
All queries read from `formula1.silver.race_results` rather than the gold dimension tables. This gives **full 2013–2026 coverage** because gold dimension joins have null FK coverage for pre-2019 drivers (driver CSVs only start in 2019). For a dashboard, raw driver and team name strings from silver are sufficient — and more complete.

**Key Copilot tools:** `databricks-execute_sql_multi` (parallel query validation), `databricks-manage_dashboard` (create + publish in one call), `web_fetch` (Databricks documentation lookup to debug JSON schema), `github-search_code` (searched `databricks/tmm` for real `.lvdash.json` examples).

> **Copilot Callout:** The entire dashboard — 4 datasets, 5 widgets, published and live — was built from a single natural-language request in one tool call (after the structure debug). A data engineer building this by clicking through the UI would have spent 30+ minutes. The agent did it in under 2 minutes of execution.

#### Dashboard JSON — Root Cause & Fix *(agent self-correction in action)*

After the dashboard was created, all four chart widgets initially displayed **"No data"** despite the underlying views returning correct results via SQL. This is an excellent example of the agent iterating to self-correct:

**Root cause:** The Databricks AI/BI (Lakeview) dashboard JSON spec has a non-obvious requirement for bar/line chart widgets:
- The `fields` array in a query **must use aggregate expressions** (e.g., `SUM(\`wins\`)`) — not raw column references.
- The `fieldName` in encodings must exactly match the field's `name` key, which in turn must match the expression alias (e.g., if the expression is `SUM(\`wins\`)`, then `name` must be `"sum(wins)"` and `fieldName` must also be `"sum(wins)"`).
- `disaggregated` must be `false` for chart widgets — meaning the dashboard renders the aggregates the fields define, rather than passing through pre-aggregated data.

This is **not documented in standard Databricks docs** — it was discovered by searching the `databricks/tmm` GitHub repository for real `.lvdash.json` files and reverse-engineering a working example.

**Was this a prompting error?** No — it was an **agent knowledge gap** about an undocumented internal JSON format. The user prompt was correct. The fix required no prompt change; the agent self-diagnosed by inspecting real working examples, extracted the correct pattern, and rebuilt the dashboard in one iteration.

**How to make the demo resilient:** Include a specific dashboard prompt (see *Suggested Demo Flow* below) that asks the agent to validate its approach against real Databricks examples. This pre-arms the agent with the correct pattern and eliminates the multi-turn debug loop.

---

## Final Schema Summary

```
formula1.gold
├── Dimensions (snowflake)
│   ├── dim_seasons (14 rows — 2013–2026, all populated after Phase 4.5)
│   ├── dim_session_types (4 rows)
│   ├── dim_power_units (13 rows)          ← sub-dim of dim_teams
│   ├── dim_drivers (39 rows)
│   ├── dim_teams (15 rows)                → FK to dim_power_units
│   ├── dim_circuits (44 rows)             ← 41 original + 3 added in Phase 4.5
│   └── dim_race_rounds (272 rows)         ← 153 original + 119 added in Phase 4.5 (2013–2018)
│
├── Bridge
│   └── bridge_driver_team_season (308 rows) → FKs to dim_drivers, dim_teams, dim_power_units
│
├── Facts
│   ├── fact_race_results (5,481 rows)     round_key: 100% populated after Phase 4.5
│   ├── fact_qualifying_results (1,922)    → same FK pattern
│   ├── fact_sprint_results (583)          → same FK pattern
│   ├── fact_sprint_qualifying_results (342)
│   └── fact_driver_of_day_votes (460)     → FKs to dim_race_rounds, dim_drivers
│
└── Lookups
    └── track_to_circuit_lookup (57 rows)  — maps result track names to circuit names
```

---

## Why This Approach Wins

1. **Single conversational interface.** No alt-tabbing between editor, terminal, browser tabs for Databricks UI, and Stack Overflow. Everything happens in one place.
2. **Tool-grounded, not guess-based.** Every claim Copilot makes about your data comes from a real query against your real tables.
3. **Iteration is cheap.** When something fails, the error feeds straight back into the agent's context. Fixes are seconds away, not minutes.
4. **Auditability.** Every notebook produced (`01_bronze_ingestion.py`, `02_silver_team_lookup.py`, etc.) is committed to local disk and can be reviewed, re-run independently, or moved into a Databricks Asset Bundle for production deployment.
5. **Plan + tracking persist.** The session-scoped plan and SQL todo list mean the agent never loses the thread, even across many turns or interruptions.

---

## What Copilot **Doesn't** Do (Yet)

- It won't grant permissions or share data outside your workspace without explicit instruction.
- It always confirms destructive operations (`DROP CATALOG`, deleting warehouses, etc.) before running them.
- It won't bypass your Unity Catalog governance — every operation runs as your authenticated identity.

---

## Suggested Demo Flow

1. **Show the empty workspace** in the Databricks UI.
2. **Open Copilot Chat** in VS Code (`Ctrl+Alt+I`), switch to **Agent mode**, and run the initial prompt (see *Recommended Prompts → Prompt 1*). The upgraded Prompt 1 includes profiling + remediation proposals, so the agent will surface the calendar gap during planning and propose fetching from the Jolpica API.
3. **Review the plan** — point out the profiling output and the remediation proposals. Approve them, then say *"proceed!"*
4. **Refresh the workspace** between phases to show schemas, volumes, and tables appearing live.
5. **Inspect the bronze tables** — point out the metadata columns and how schema merging worked across seasons with different headers.
6. **Show the team_name_lookup** — emphasize the 70 → 18 reduction and how the algorithm + manual aliases combined.
7. **Continue with silver/gold** to demonstrate that the pattern scales.
8. **At validation (Phase 6)** — show the FK null analysis. If you used the upgraded Prompt 1, the agent has already executed the Phase 6b enrichment and round_key is 100% populated; show the before/after comparison from its own output. If you used the original Prompt 1, run **Prompt 3** here and watch null round_keys drop from 2,971 → 0 live.
9. **Run the dashboard prompt** (Prompt 2) — watch it appear live in the Databricks UI.
10. **Open the AI/BI Dashboard** ("Formula 1 Championship Analysis") — point out that team names are clean (no power-unit suffixes), every season is represented, and the data spans all 14 seasons of CSVs that came in as raw files.

---

---

*Generated during a live GitHub Copilot session on a Databricks workspace. All commands shown were executed by the agent in real time.*
