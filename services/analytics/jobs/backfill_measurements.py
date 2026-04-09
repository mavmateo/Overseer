"""Backfill batch aggregates from historical measurements."""

from __future__ import annotations

from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col


def main() -> None:
    spark = SparkSession.builder.appName("og-measurement-backfill").getOrCreate()
    frame = (
        spark.read.format("jdbc")
        .option("url", "jdbc:postgresql://timescaledb:5432/og_iot")
        .option("dbtable", "measurements")
        .option("user", "postgres")
        .option("password", "postgres")
        .load()
    )
    summary = frame.groupBy(col("site_id"), col("asset_id"), col("signal_id")).agg(avg("value").alias("avg_value"))
    summary.write.mode("overwrite").format("jdbc").option("url", "jdbc:postgresql://timescaledb:5432/og_iot").option(
        "dbtable", "measurement_backfill_summary"
    ).option("user", "postgres").option("password", "postgres").save()


if __name__ == "__main__":
    main()

