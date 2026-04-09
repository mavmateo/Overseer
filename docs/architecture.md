# Architecture Overview

## Topology

- Each site runs a K3s edge cluster in the site DMZ.
- EdgeX integrates with OT protocols and normalizes device data.
- Mosquitto is the first landing point for telemetry, events, alarms, and command acknowledgements.
- The site forwarder persists MQTT payloads to local disk and forwards them to central Kafka after validation.
- Central services consume Kafka and persist operational history to TimescaleDB.
- FastAPI exposes operational APIs and GraphQL, while Grafana serves dashboards for operators and platform teams.
- TensorFlow models are trained centrally and deployed to edge inference runtimes when latency requires it.

## Data Flow

1. Device services publish telemetry to `Mosquitto`.
2. The site forwarder validates each payload against the canonical envelope and appends it to a local spool.
3. The forwarder publishes to Kafka with an idempotent key derived from `eventId` or `(siteId, signalId, ts_source, seq)`.
4. Spark jobs build features, aggregates, and model inputs from Kafka.
5. TimescaleDB stores raw measurements, alarms, events, state, command logs, and model scores.
6. FastAPI and GraphQL serve operators, automation workflows, and dashboards.

## Command Safety

- Commands are modeled as approval-gated requests, not direct control writes.
- Node-RED may publish only approved command envelopes to approved topics.
- High-impact commands must be approved by a human and reconciled against acknowledgements plus final asset state.
- Safety PLC, SIS, and ESD boundaries stay outside this platform.

