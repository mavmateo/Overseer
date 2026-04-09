#!/usr/bin/env bash
set -euo pipefail

topics=(
  raw.telemetry
  raw.events
  raw.alarms
  asset.state
  command.request
  command.ack
  analytics.features
  analytics.inference
  platform.audit
  security.audit
)

for topic in "${topics[@]}"; do
  kafka-topics.sh \
    --bootstrap-server kafka:9092 \
    --create \
    --if-not-exists \
    --topic "${topic}" \
    --partitions 3 \
    --replication-factor 1
done

