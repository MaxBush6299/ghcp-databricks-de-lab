# Databricks notebook source
# MAGIC %md
# MAGIC # Phase 4.5 — Calendar Enrichment (2013–2018)
# MAGIC
# MAGIC **Why this notebook exists:**
# MAGIC The gold `dim_race_rounds` table was originally built from CSV calendar files only available for
# MAGIC 2019–2026. This left ~50% of `fact_race_results.round_key` values NULL for pre-2019 seasons.
# MAGIC
# MAGIC **Approach:**
# MAGIC 1. Fix silver data quality issues (typos in circuit_name)
# MAGIC 2. Add missing circuits to `dim_circuits` (Korea, India, Malaysia)
# MAGIC 3. Fetch 2013–2018 calendars from the free **Jolpica API** (Ergast replacement)
# MAGIC 4. Insert new rows into `dim_race_rounds`
# MAGIC 5. Backfill `fact_race_results.round_key` for all previously-null rows
# MAGIC
# MAGIC **Data quality issues found and fixed:**
# MAGIC - `silver.race_results`: "Sinagpore" (2016, 1 row) → "Singapore"
# MAGIC - `silver.race_results`: "Great Brtiain" (2017, 1 row) → "Great Britain"
# MAGIC - `gold.track_to_circuit_lookup`: "United States" → was "Las Vegas Strip Circuit", corrected to "Circuit of The Americas" (COTA) for pre-2023 accuracy
# MAGIC - `dim_circuits`: "Sliverstone Circuit" (key 37) is a typo duplicate — legitimate key 36 "Silverstone Circuit" used for all joins

# COMMAND ----------

import requests
import json

catalog = "formula1"

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 1: Fix Silver Data Quality Issues

# COMMAND ----------

# Fix "Sinagpore" typo in 2016
spark.sql(f"""
UPDATE {catalog}.silver.race_results
SET circuit_name = 'Singapore'
WHERE circuit_name = 'Sinagpore' AND _season_year = 2016
""")
print("Fixed: 'Sinagpore' → 'Singapore' (2016)")

# Fix "Great Brtiain" typo in 2017
spark.sql(f"""
UPDATE {catalog}.silver.race_results
SET circuit_name = 'Great Britain'
WHERE circuit_name = 'Great Brtiain' AND _season_year = 2017
""")
print("Fixed: 'Great Brtiain' → 'Great Britain' (2017)")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 2: Add Missing Circuits to dim_circuits

# COMMAND ----------

# Get the current max circuit_key so we can assign new ones
max_key = spark.sql(f"SELECT MAX(circuit_key) AS mk FROM {catalog}.gold.dim_circuits").collect()[0]["mk"]
print(f"Current max circuit_key: {max_key}")

new_circuits_sql = [
    (max_key + 1, "Korean International Circuit", "South Korea", "Yeongam",       5.615, 18, 3, 2010),
    (max_key + 2, "Buddh International Circuit",  "India",       "Greater Noida", 5.125, 16, 3, 2011),
    (max_key + 3, "Sepang International Circuit", "Malaysia",    "Kuala Lumpur",  5.543, 15, 2, 1999),
]

for ck_val, cname, country, city, length, turns, drs, first_year in new_circuits_sql:
    spark.sql(f"""
    INSERT INTO {catalog}.gold.dim_circuits (circuit_key, circuit_name, country, city, circuit_length_km, turns, drs_zones, first_gp_year)
    VALUES ({ck_val}, '{cname}', '{country}', '{city}', {length}, {turns}, {drs}, {first_year})
    """)
    print(f"Inserted: {cname} ({country})")

# Retrieve the actual assigned keys (in case of concurrent writes)
circuit_df = spark.sql(f"SELECT circuit_key, circuit_name FROM {catalog}.gold.dim_circuits WHERE circuit_name IN ('Korean International Circuit', 'Buddh International Circuit', 'Sepang International Circuit')")
circuit_df.show(truncate=False)

circuit_key_map = {row["circuit_name"]: row["circuit_key"] for row in circuit_df.collect()}
print("New circuit keys:", circuit_key_map)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 3: Build Circuit-ID → (circuit_key, silver_track_name) Lookup

# COMMAND ----------

# Fetch existing circuit keys we need for mapping
existing = spark.sql(f"""
SELECT circuit_key, circuit_name FROM {catalog}.gold.dim_circuits
WHERE circuit_name IN (
  'Albert Park Circuit',
  'Bahrain International Circuit',
  'Shanghai International Circuit',
  'Circuit de Barcelona-Catalunya',
  'Circuit de Monaco',
  'Circuit Gilles-Villeneuve',
  'Silverstone Circuit',
  'Nurburgring',
  'Hockenheimring',
  'Hungaroring',
  'Circuit de Spa-Francorchamps',
  'Autodromo Nazionale Monza',
  'Marina Bay Street Circuit',
  'Suzuka Circuit',
  'Circuit of The Americas',
  'Autodromo Jose Carlos Pace',
  'Yas Marina Circuit',
  'Baku City Circuit',
  'Red Bull Ring',
  'Sochi Autodrom',
  'Autodromo Hermanos Rodriguez',
  'Circuit Paul Ricard'
)
""").collect()

ck = {row["circuit_name"]: row["circuit_key"] for row in existing}
print("Loaded circuit keys:", ck)

# COMMAND ----------

# Jolpica circuitId → (dim_circuits circuit_name for lookup, silver track_name)
# Note: Baku is year-dependent for track_name ("Europe" in 2016, "Azerbaijan" from 2017)
CIRCUIT_MAP = {
    "albert_park":   (ck.get("Albert Park Circuit"),                    "Australia"),
    "bahrain":       (ck.get("Bahrain International Circuit"),           "Bahrain"),
    "shanghai":      (ck.get("Shanghai International Circuit"),          "China"),
    "catalunya":     (ck.get("Circuit de Barcelona-Catalunya"),          "Spain"),
    "monaco":        (ck.get("Circuit de Monaco"),                       "Monaco"),
    "villeneuve":    (ck.get("Circuit Gilles-Villeneuve"),               "Canada"),
    "silverstone":   (ck.get("Silverstone Circuit"),                     "Great Britain"),
    "nurburgring":   (ck.get("Nurburgring"),                             "Germany"),
    "hockenheimring":(ck.get("Hockenheimring"),                          "Germany"),
    "hungaroring":   (ck.get("Hungaroring"),                             "Hungary"),
    "spa":           (ck.get("Circuit de Spa-Francorchamps"),            "Belgium"),
    "monza":         (ck.get("Autodromo Nazionale Monza"),               "Italy"),
    "yeongam":       (circuit_key_map.get("Korean International Circuit"), "South Korea"),
    "buddh":         (circuit_key_map.get("Buddh International Circuit"),  "India"),
    "marina_bay":    (ck.get("Marina Bay Street Circuit"),               "Singapore"),
    "suzuka":        (ck.get("Suzuka Circuit"),                          "Japan"),
    "americas":      (ck.get("Circuit of The Americas"),                 "United States"),
    "interlagos":    (ck.get("Autodromo Jose Carlos Pace"),              "Brazil"),
    "yas_marina":    (ck.get("Yas Marina Circuit"),                      "Abu Dhabi"),
    "sepang":        (circuit_key_map.get("Sepang International Circuit"), "Malaysia"),
    "baku":          (ck.get("Baku City Circuit"),                       None),  # year-dependent, handled below
    "red_bull_ring": (ck.get("Red Bull Ring"),                           "Austria"),
    "sochi":         (ck.get("Sochi Autodrom"),                          "Russia"),
    "rodriguez":     (ck.get("Autodromo Hermanos Rodriguez"),            "Mexico"),
    "ricard":        (ck.get("Circuit Paul Ricard"),                     "France"),
}

print("CIRCUIT_MAP loaded. Unmapped entries:", [(k, v) for k, v in CIRCUIT_MAP.items() if v[0] is None])

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 4: Fetch Jolpica API for 2013–2018

# COMMAND ----------

def fetch_jolpica_calendar(year):
    """Fetch a single season's race calendar from Jolpica API."""
    url = f"https://api.jolpi.ca/ergast/f1/{year}/races.json?limit=30"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    races = data["MRData"]["RaceTable"]["Races"]
    print(f"  {year}: {len(races)} races fetched")
    return races

all_races = {}
for year in range(2013, 2019):
    print(f"Fetching {year}...")
    all_races[year] = fetch_jolpica_calendar(year)

total = sum(len(v) for v in all_races.values())
print(f"\nTotal races fetched: {total}")

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 5: Build dim_race_rounds Rows for 2013–2018

# COMMAND ----------

from datetime import datetime

def get_circuit_key_and_track_name(circuit_id, year):
    """Resolve Jolpica circuitId → (circuit_key, track_name) with year-aware overrides."""
    entry = CIRCUIT_MAP.get(circuit_id)
    if entry is None:
        print(f"  WARNING: No mapping for circuitId '{circuit_id}' ({year}). Skipping.")
        return None, None

    circuit_key, track_name = entry

    # Year-dependent track_name overrides
    if circuit_id == "baku":
        track_name = "Europe" if year == 2016 else "Azerbaijan"

    if circuit_key is None:
        print(f"  WARNING: circuit_key is None for circuitId '{circuit_id}' ({year}).")

    return circuit_key, track_name


# Get existing dim_race_rounds seasons to avoid duplicate inserts
existing_seasons = set(
    row["season_year"]
    for row in spark.sql(f"SELECT DISTINCT season_year FROM {catalog}.gold.dim_race_rounds").collect()
)
print(f"Existing season_years in dim_race_rounds: {sorted(existing_seasons)}")

rounds_to_insert = []

for year, races in all_races.items():
    if year in existing_seasons:
        print(f"Season {year} already in dim_race_rounds — skipping.")
        continue

    for race in races:
        circuit_id = race["Circuit"]["circuitId"]
        circuit_key, track_name = get_circuit_key_and_track_name(circuit_id, year)

        if circuit_key is None or track_name is None:
            continue

        round_number = int(race["round"])
        race_date_str = race.get("date", None)
        race_date = datetime.strptime(race_date_str, "%Y-%m-%d").date() if race_date_str else None
        official_gp_name = race.get("raceName", "")

        rounds_to_insert.append({
            "season_year": year,
            "circuit_key": circuit_key,
            "track_name": track_name,
            "round_number": round_number,
            "race_date": race_date,
            "official_gp_name": official_gp_name,
            "number_of_laps": None,
            "race_distance_km": None,
            "lap_record": None,
            "record_owner": None,
            "record_year": None,
        })

print(f"\nRounds prepared for insert: {len(rounds_to_insert)}")
for r in sorted(rounds_to_insert, key=lambda x: (x["season_year"], x["round_number"]))[:10]:
    print(f"  {r['season_year']} R{r['round_number']:02d}: {r['track_name']} ({r['official_gp_name']}) → circuit_key={r['circuit_key']}")

# COMMAND ----------

# Also need to add 2013-2018 to dim_seasons if not present
existing_seasons_dim = set(
    row["season_year"]
    for row in spark.sql(f"SELECT DISTINCT season_year FROM {catalog}.gold.dim_seasons").collect()
)
print(f"Existing dim_seasons: {sorted(existing_seasons_dim)}")

missing_seasons_data = []
for year, races in all_races.items():
    if year not in existing_seasons_dim:
        missing_seasons_data.append({"season_year": year, "total_rounds": len(races)})

if missing_seasons_data:
    for s in missing_seasons_data:
        spark.sql(f"INSERT INTO {catalog}.gold.dim_seasons (season_year, total_rounds) VALUES ({s['season_year']}, {s['total_rounds']})")
    print(f"Inserted {len(missing_seasons_data)} seasons into dim_seasons: {[s['season_year'] for s in missing_seasons_data]}")
else:
    print("All seasons already in dim_seasons.")

# COMMAND ----------

# Insert new dim_race_rounds rows
if rounds_to_insert:
    # Get current max round_key to generate new ones
    max_rk = spark.sql(f"SELECT COALESCE(MAX(round_key), 0) AS mrk FROM {catalog}.gold.dim_race_rounds").collect()[0]["mrk"]
    print(f"Current max round_key: {max_rk}")

    inserted = 0
    for r in rounds_to_insert:
        max_rk += 1
        race_date_val = f"DATE '{r['race_date']}'" if r['race_date'] else "NULL"
        gp_name_escaped = r['official_gp_name'].replace("'", "''")
        track_escaped = r['track_name'].replace("'", "''")
        spark.sql(f"""
        INSERT INTO {catalog}.gold.dim_race_rounds
          (round_key, season_year, circuit_key, track_name, round_number, race_date, official_gp_name,
           number_of_laps, race_distance_km, lap_record, record_owner, record_year)
        VALUES
          ({max_rk}, {r['season_year']}, {r['circuit_key']}, '{track_escaped}', {r['round_number']},
           {race_date_val}, '{gp_name_escaped}',
           NULL, NULL, NULL, NULL, NULL)
        """)
        inserted += 1
    print(f"Inserted {inserted} rows into dim_race_rounds")
else:
    print("No new rows to insert (all seasons already present).")

# Verify
spark.sql(f"""
SELECT season_year, COUNT(*) as rounds 
FROM {catalog}.gold.dim_race_rounds 
GROUP BY season_year ORDER BY season_year
""").show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 6: Backfill fact_race_results.round_key

# COMMAND ----------

# Check current null state
null_before = spark.sql(f"""
SELECT COUNT(*) AS null_round_keys 
FROM {catalog}.gold.fact_race_results 
WHERE round_key IS NULL
""").collect()[0]["null_round_keys"]
print(f"Null round_keys BEFORE backfill: {null_before}")

# COMMAND ----------

# Backfill: join fact to dim_race_rounds via (season_year, track_name) → round_key
spark.sql(f"""
UPDATE {catalog}.gold.fact_race_results AS f
SET f.round_key = d.round_key
FROM {catalog}.gold.dim_race_rounds AS d
WHERE f.round_key IS NULL
  AND f.season_year = d.season_year
  AND f.track_name  = d.track_name
""")

# COMMAND ----------

null_after = spark.sql(f"""
SELECT COUNT(*) AS null_round_keys 
FROM {catalog}.gold.fact_race_results 
WHERE round_key IS NULL
""").collect()[0]["null_round_keys"]
print(f"Null round_keys AFTER backfill: {null_after}")
print(f"Round keys resolved: {null_before - null_after}")

# COMMAND ----------

# If any nulls remain, investigate
if null_after > 0:
    print("\nRemaining unmatched (season_year + track_name combos not in dim_race_rounds):")
    spark.sql(f"""
    SELECT f.season_year, f.track_name, COUNT(*) as rows
    FROM {catalog}.gold.fact_race_results f
    WHERE f.round_key IS NULL
    GROUP BY f.season_year, f.track_name
    ORDER BY f.season_year, f.track_name
    """).show(50, truncate=False)

# COMMAND ----------
# MAGIC %md
# MAGIC ## Step 7: Validate Gold Views Still Work

# COMMAND ----------

print("=== Driver wins by season (2013–2015 sample) ===")
spark.sql(f"""
SELECT season_year, driver_name, wins
FROM {catalog}.gold.vw_driver_wins
WHERE season_year BETWEEN 2013 AND 2015
ORDER BY season_year, wins DESC
""").show(30)

# COMMAND ----------

print("=== Constructor wins (hybrid era 2014–2015) ===")
spark.sql(f"""
SELECT season_year, team_short_name, wins
FROM {catalog}.gold.vw_constructor_wins
WHERE season_year IN (2014, 2015)
ORDER BY season_year, wins DESC
""").show()

# COMMAND ----------
# MAGIC %md
# MAGIC ## Summary
# MAGIC
# MAGIC | Step | Result |
# MAGIC |------|--------|
# MAGIC | Silver typo fixes | "Sinagpore" → "Singapore", "Great Brtiain" → "Great Britain" |
# MAGIC | New circuits added | Korean Int'l, Buddh Int'l, Sepang Int'l |
# MAGIC | dim_seasons updated | 2013–2018 rows added |
# MAGIC | dim_race_rounds updated | ~116 rows added for 2013–2018 |
# MAGIC | fact_race_results backfill | round_key nulls resolved from ~50% → near 0% |
