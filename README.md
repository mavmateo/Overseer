# Open Industrial IoT Platform

This repository implements a production-oriented, fully open-source industrial IoT platform scaffold for oil & gas and mining. It includes edge-to-core message contracts, Kubernetes and local development infrastructure, a FastAPI application layer, a store-and-forward MQTT-to-Kafka bridge, Spark and TensorFlow job skeletons, and dummy sensor simulators.

## Repository Layout

- `shared/python/iot_platform`: canonical topic builders, Kafka topic names, and contract validation helpers.
- `services/backend`: FastAPI service with REST APIs and GraphQL endpoint for telemetry, alarms, model deployment, and command workflows.
- `services/site-forwarder`: edge service that buffers MQTT messages locally and forwards them to Kafka with dedupe-safe keys.
- `services/ingestor`: Kafka consumer that persists telemetry, alarms, events, asset state, commands, and inference results into TimescaleDB.
- `services/simulator`: dummy industrial sensor simulator for pumps, crushers, conveyors, tanks, and gas detection signals.
- `services/analytics`: Spark jobs for stream processing and backfills.
- `services/mlops`: TensorFlow training and edge inference stubs.
- `services/live-feed-adapter`: Node.js sidecar for high-volume live-feed fan-out.
- `infra`: Docker Compose, TimescaleDB schema, Mosquitto config, OpenBao policies, Grafana provisioning, and Kubernetes manifests.
- `docs`: architecture notes and runbooks.
- `tests`: contract and topic tests that run without a full cluster.

## Quick Start

1. Copy `.env.example` to `.env` and adjust credentials or image overrides as needed.
2. Review `infra/docker-compose.dev.yml` for local development defaults.
3. Start the local stack with `docker compose -f infra/docker-compose.dev.yml up --build`.
4. Run repository checks with `make test` and `make check-python`.
5. Verify Kafka-to-TimescaleDB ingestion by consuming a few messages from Kafka and querying `measurements` in TimescaleDB.

## End-to-End Smoke Test

1. Start the stack with `docker compose -f infra/docker-compose.dev.yml up --build`.
2. Check that the simulator is publishing and the site forwarder is buffering/forwarding:
   - `docker compose -f infra/docker-compose.dev.yml logs -f simulator site-forwarder ingestor`
3. Confirm the API is up:
   - `curl http://localhost:8000/healthz`
4. Confirm Kafka has telemetry:
   - `docker compose -f infra/docker-compose.dev.yml exec kafka /opt/kafka/bin/kafka-console-consumer.sh --bootstrap-server kafka:9092 --topic raw.telemetry --from-beginning --max-messages 5`
   - If you connect from the host instead of `docker compose exec`, use `localhost:29092`.
5. Confirm TimescaleDB has ingested rows:
   - `docker compose -f infra/docker-compose.dev.yml exec timescaledb psql -U postgres -d og_iot -c "SELECT asset_id, signal_id, value, ts_source FROM measurements ORDER BY ts_source DESC LIMIT 10;"`
6. Open Grafana at `http://localhost:3000` and view the `Platform Overview` dashboard.

## Key Interfaces

- MQTT topic: `site/{siteId}/area/{areaId}/asset/{assetId}/{channel}`
- REST endpoints:
  - `POST /commands`
  - `GET /assets/{assetId}/telemetry`
  - `GET /alarms`
  - `POST /models/deploy`
  - `GET /sites/{siteId}/health`
  - `GET /platform/ingest-status`
- GraphQL endpoint: `POST /graphql`

## Delivery Notes

- The scaffold is intentionally opinionated around hub-and-spoke deployment, intermittent WAN, and non-safety control boundaries.
- Third-party platform components are represented via Helm values and deployment conventions rather than vendored charts.
- Pin container images and dependency versions in environment-specific promotion pipelines before production rollout.

# Overseer
