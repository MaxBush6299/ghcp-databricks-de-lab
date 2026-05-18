"""
Silver — Team Name Normalization Lookup

Builds formula1.silver.team_name_lookup mapping every observed team name
variant (across race_results, qualifying, sprint, drivers, teams) to a
canonical team_short_name and (where applicable) a power_unit.

Algorithm:
  - Canonical short names come from formula1.bronze.raw_teams.team
  - Race/qualifying/sprint results use "<short_name> <power_unit>" format
    (e.g., "Red Bull Racing Honda RBPT", "McLaren Mercedes")
  - Match each variant against canonical short names by longest-prefix match
  - Strip the prefix to get the power unit
  - Manual overrides handle historical edge cases (Alfa Romeo Racing -> Alfa Romeo, etc.)
"""

from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType


# ---------------------------------------------------------------------------
# 1. Gather canonical short names from raw_teams across all seasons
# ---------------------------------------------------------------------------
canonical_rows = (
    spark.sql(
        """
        SELECT DISTINCT team AS short_name
        FROM formula1.bronze.raw_teams
        WHERE team IS NOT NULL
        """
    ).collect()
)
canonical_short_names = sorted({r["short_name"].strip() for r in canonical_rows}, key=len, reverse=True)


# ---------------------------------------------------------------------------
# 2. Manual aliases for historical team names not present in raw_teams
#    (these existed before our drivers/teams files began in 2021/2019)
# ---------------------------------------------------------------------------
HISTORICAL_ALIASES = {
    # Exact-match renames (no power unit suffix expected in source data)
    "Alfa Romeo Racing": "Alfa Romeo",
    "Racing Point": "Aston Martin",
    "Toro Rosso": "AlphaTauri",
    "Scuderia Toro Rosso": "AlphaTauri",
    "STR": "AlphaTauri",
    "Force India": "Aston Martin",
    "Renault": "Alpine",
    "Sauber": "Kick Sauber",
    "Manor Marussia": "Manor",
    "Marussia": "Manor",
    "MRT": "Manor",
    "Haas F1 Team": "Haas",
    "Red Bull": "Red Bull Racing",
    "Racing bulls": "Racing Bulls",
    "Racing Honda RBPT": "Racing Bulls",
    "Aston Martib Aramco Mercedes": "Aston Martin",
    "Aston Martib": "Aston Martin",
    "Williams Meredes": "Williams",
    # Prefix aliases — power unit suffix WILL be extracted after the prefix
    # Cadillac Formula 1 Team: uses Ferrari power unit (2026)
    "Cadillac": "Cadillac",
    # Lotus F1 Team (Enstone, 2012-2015): used Renault, then Mercedes, then Ferrari
    "Lotus": "Lotus",
    # Caterham F1 Team (2012-2014): used Renault throughout
    "Caterham": "Caterham",
}


# ---------------------------------------------------------------------------
# 3. Gather every team-name variant across results tables
# ---------------------------------------------------------------------------
variants_df = spark.sql(
    """
    SELECT DISTINCT team AS variant FROM formula1.bronze.raw_race_results WHERE team IS NOT NULL
    UNION
    SELECT DISTINCT team AS variant FROM formula1.bronze.raw_qualifying  WHERE team IS NOT NULL
    UNION
    SELECT DISTINCT team AS variant FROM formula1.bronze.raw_sprint      WHERE team IS NOT NULL
    UNION
    SELECT DISTINCT team AS variant FROM formula1.bronze.raw_sprint_qualifying WHERE team IS NOT NULL
    UNION
    SELECT DISTINCT team AS variant FROM formula1.bronze.raw_drivers     WHERE team IS NOT NULL
    UNION
    SELECT DISTINCT team AS variant FROM formula1.bronze.raw_teams       WHERE team IS NOT NULL
    """
)
variants = [r["variant"].strip() for r in variants_df.collect()]


# ---------------------------------------------------------------------------
# 4. Resolve each variant to a canonical short name + power unit
# ---------------------------------------------------------------------------
def resolve(variant: str):
    v = variant.strip()
    v_lower = v.lower()

    # Exact alias match
    if v in HISTORICAL_ALIASES:
        return HISTORICAL_ALIASES[v], None

    # Exact canonical short-name match (case-insensitive)
    for short in canonical_short_names:
        if v_lower == short.lower():
            return short, None

    # Canonical short-name as prefix (case-insensitive)
    for short in canonical_short_names:
        if v_lower.startswith(short.lower() + " "):
            return short, v[len(short) + 1:].strip()

    # Historical alias as prefix
    for hist, canonical in HISTORICAL_ALIASES.items():
        if v_lower.startswith(hist.lower() + " "):
            return canonical, v[len(hist) + 1:].strip()

    return v, None


lookup_rows = [(v, *resolve(v)) for v in sorted(set(variants))]


# ---------------------------------------------------------------------------
# 5. Persist as Delta
# ---------------------------------------------------------------------------
schema = StructType([
    StructField("team_variant",     StringType(), False),
    StructField("team_short_name",  StringType(), False),
    StructField("power_unit",       StringType(), True),
])
lookup_df = spark.createDataFrame(lookup_rows, schema=schema)

(
    lookup_df.write
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable("formula1.silver.team_name_lookup")
)

# ---------------------------------------------------------------------------
# 6. Show what was built (writes to a temp summary table for inspection)
# ---------------------------------------------------------------------------
summary_df = (
    spark.table("formula1.silver.team_name_lookup")
         .groupBy("team_short_name")
         .agg(
             F.countDistinct("team_variant").alias("variant_count"),
             F.collect_set("team_variant").alias("variants"),
             F.collect_set("power_unit").alias("power_units"),
         )
         .orderBy("team_short_name")
)
(
    summary_df.write
        .mode("overwrite")
        .option("overwriteSchema", "true")
        .saveAsTable("formula1.silver._team_name_lookup_summary")
)
