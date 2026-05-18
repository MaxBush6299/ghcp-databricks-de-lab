"""
Bronze Layer Ingestion — Formula 1
Reads all CSVs from /Volumes/formula1/raw/csvs/<source_type>/ and writes
to formula1.bronze.raw_<source_type> Delta tables.

Adds metadata columns:
  _source_file        — original filename
  _ingestion_timestamp — when this row was loaded
  _season_year        — parsed from filename (4-digit year)
"""

from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType
import re

VOLUME_BASE = "/Volumes/formula1/raw/csvs"
BRONZE_SCHEMA = "formula1.bronze"

SOURCE_TYPES = [
    "race_results",
    "qualifying",
    "sprint",
    "sprint_qualifying",
    "drivers",
    "teams",
    "calendar",
    "dotd_votes",
    "videogame_ratings",
]


def sanitize(name: str) -> str:
    s = re.sub(r"[ ,;{}()\n\t=./+\-]+", "_", name.strip())
    s = re.sub(r"_+", "_", s)
    if not name.startswith("_"):
        s = s.strip("_")
    else:
        s = "_" + s.strip("_")
    return s.lower()


results = []

for source_type in SOURCE_TYPES:
    src_path = f"{VOLUME_BASE}/{source_type}/*.csv"
    table_name = f"{BRONZE_SCHEMA}.raw_{source_type}"

    df = (
        spark.read
            .option("header", "true")
            .option("inferSchema", "false")
            .option("mergeSchema", "true")
            .option("multiLine", "true")
            .option("escape", '"')
            .csv(src_path)
            .withColumn("_source_file", F.element_at(F.split(F.col("_metadata.file_path"), "/"), -1))
            .withColumn("_ingestion_timestamp", F.current_timestamp())
            .withColumn(
                "_season_year",
                F.expr("try_cast(regexp_extract(_source_file, '(\\\\d{4})', 1) AS INT)"),
            )
    )

    sanitized = df.toDF(*[sanitize(c) for c in df.columns])

    (
        sanitized.write
          .mode("overwrite")
          .option("overwriteSchema", "true")
          .saveAsTable(table_name)
    )

    cnt = spark.table(table_name).count()
    seasons = [r[0] for r in spark.table(table_name)
                              .select("_season_year").distinct()
                              .orderBy("_season_year").collect()]
    results.append((source_type, cnt, seasons))
    print(f"  {source_type}: {cnt} rows, seasons={seasons}")

print("\n=== BRONZE INGESTION SUMMARY ===")
for s, c, y in results:
    print(f"  raw_{s}: {c:>5} rows  | seasons: {y}")
