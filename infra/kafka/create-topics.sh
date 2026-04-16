#!/bin/sh
set -eu

KAFKA_TOPICS_BIN="/opt/kafka/bin/kafka-topics.sh"

until "${KAFKA_TOPICS_BIN}" --bootstrap-server kafka:9092 --list >/dev/null 2>&1; do
  sleep 2
done

for topic in \
  raw.telemetry \
  raw.events \
  raw.alarms \
  asset.state \
  command.request \
  command.ack \
  analytics.features \
  analytics.inference \
  platform.audit \
  security.audit
do
  "${KAFKA_TOPICS_BIN}" \
    --bootstrap-server kafka:9092 \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions 3 \
    --replication-factor 1
done
