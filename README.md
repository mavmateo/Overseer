# Open Industrial IoT Platform

This repository implements a production-oriented, fully open-source industrial IoT platform scaffold for oil & gas and mining. It includes edge-to-core message contracts, Kubernetes and local development infrastructure, a FastAPI application layer, a store-and-forward MQTT-to-Kafka bridge, Spark and TensorFlow job skeletons, and dummy sensor simulators.

## Repository Layout

- `shared/python/iot_platform`: canonical topic builders, Kafka topic names, and contract validation helpers.
- `services/backend`: FastAPI service with REST APIs and GraphQL endpoint for telemetry, alarms, model deployment, and command workflows.
- `services/site-forwarder`: edge service that buffers MQTT messages locally and forwards them to Kafka with dedupe-safe keys.
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
4. Run contract checks with `PYTHONPATH=shared/python python3 -m unittest discover -s tests/contracts`.
5. Start the simulator with `python3 services/simulator/app/main.py`.

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
