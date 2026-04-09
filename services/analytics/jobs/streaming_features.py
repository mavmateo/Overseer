"""Spark job that transforms raw telemetry into rolling feature windows."""

from __future__ import annotations

from pyspark.sql import SparkSession
from pyspark.sql.functions import avg, col, from_json, to_json, struct, window
from pyspark.sql.types import (
    DoubleType,
    IntegerType,
    MapType,
    StringType,
    StructField,
    StructType,
)

telemetry_schema = StructType(
    [
        StructField("eventId", StringType(), False),
        StructField("siteId", StringType(), False),
        StructField("assetId", StringType(), False),
        StructField("signalId", StringType(), False),
        StructField("quality", StringType(), False),
        StructField("ts_source", StringType(), False),
        StructField("ts_ingest", StringType(), False),
        StructField("seq", IntegerType(), False),
        StructField("unit", StringType(), False),
        StructField("value", DoubleType(), False),
        StructField("tags", MapType(StringType(), StringType()), True),
        StructField("traceId", StringType(), True),
    ]
)


def main() -> None:
    spark = SparkSession.builder.appName("og-telemetry-features").getOrCreate()
    raw = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("subscribe", "raw.telemetry")
        .option("startingOffsets", "latest")
        .load()
    )
    parsed = raw.select(from_json(col("value").cast("string"), telemetry_schema).alias("payload")).select("payload.*")
    features = (
        parsed.withWatermark("ts_source", "10 minutes")
        .groupBy(window("ts_source", "1 minute"), col("siteId"), col("assetId"), col("signalId"))
        .agg(avg("value").alias("avg_value"))
        .select(
            to_json(
                struct(
                    col("siteId"),
                    col("assetId"),
                    col("signalId"),
                    col("window.start").alias("windowStart"),
                    col("window.end").alias("windowEnd"),
                    col("avg_value"),
                )
            ).alias("value")
        )
    )
    query = (
        features.writeStream.format("kafka")
        .option("kafka.bootstrap.servers", "kafka:9092")
        .option("topic", "analytics.features")
        .option("checkpointLocation", "/tmp/og-telemetry-features")
        .start()
    )
    query.awaitTermination()


if __name__ == "__main__":
    main()

