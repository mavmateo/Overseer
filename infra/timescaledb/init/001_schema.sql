CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS asset_registry (
    asset_id TEXT PRIMARY KEY,
    site_id TEXT NOT NULL,
    area_id TEXT NOT NULL,
    name TEXT NOT NULL,
    protocol TEXT NOT NULL DEFAULT 'mqtt',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS signal_registry (
    asset_id TEXT NOT NULL REFERENCES asset_registry (asset_id) ON DELETE CASCADE,
    signal_id TEXT NOT NULL,
    unit TEXT NOT NULL,
    sampling_class TEXT NOT NULL,
    PRIMARY KEY (asset_id, signal_id)
);

CREATE TABLE IF NOT EXISTS measurements (
    ts_source TIMESTAMPTZ NOT NULL,
    ts_ingest TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    event_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    seq BIGINT NOT NULL,
    quality TEXT NOT NULL,
    unit TEXT NOT NULL,
    value DOUBLE PRECISION NOT NULL,
    tags JSONB NOT NULL DEFAULT '{}'::jsonb,
    trace_id TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (ts_source, asset_id, signal_id, seq)
);
SELECT create_hypertable('measurements', by_range('ts_source'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS events (
    ts_source TIMESTAMPTZ NOT NULL,
    event_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (ts_source, event_id)
);
SELECT create_hypertable('events', by_range('ts_source'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS alarms (
    raised_at TIMESTAMPTZ NOT NULL,
    alarm_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    severity TEXT NOT NULL,
    message TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'open',
    acknowledged_at TIMESTAMPTZ,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (raised_at, alarm_id)
);
SELECT create_hypertable('alarms', by_range('raised_at'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS command_log (
    issued_at TIMESTAMPTZ NOT NULL,
    command_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    target_signal TEXT NOT NULL,
    requested_value TEXT NOT NULL,
    requested_by TEXT NOT NULL,
    priority TEXT NOT NULL,
    approved BOOLEAN NOT NULL DEFAULT FALSE,
    approval_reference TEXT NOT NULL DEFAULT '',
    expires_at TIMESTAMPTZ NOT NULL,
    status TEXT NOT NULL,
    PRIMARY KEY (issued_at, command_id)
);
SELECT create_hypertable('command_log', by_range('issued_at'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS asset_state (
    ts_source TIMESTAMPTZ NOT NULL,
    site_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    state TEXT NOT NULL,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts_source, asset_id)
);
SELECT create_hypertable('asset_state', by_range('ts_source'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS model_registry (
    deployed_at TIMESTAMPTZ NOT NULL,
    model_id TEXT NOT NULL,
    version TEXT NOT NULL,
    checksum TEXT NOT NULL,
    input_schema TEXT NOT NULL,
    approval_state TEXT NOT NULL,
    target_scope TEXT NOT NULL,
    rollback_version TEXT NOT NULL DEFAULT '',
    deployed_by TEXT NOT NULL,
    PRIMARY KEY (deployed_at, model_id, version)
);
SELECT create_hypertable('model_registry', by_range('deployed_at'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS model_scores (
    ts_source TIMESTAMPTZ NOT NULL,
    model_id TEXT NOT NULL,
    site_id TEXT NOT NULL,
    asset_id TEXT NOT NULL,
    signal_id TEXT NOT NULL,
    score DOUBLE PRECISION NOT NULL,
    anomalous BOOLEAN NOT NULL DEFAULT FALSE,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (ts_source, model_id, asset_id, signal_id)
);
SELECT create_hypertable('model_scores', by_range('ts_source'), if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS site_health (
    updated_at TIMESTAMPTZ NOT NULL,
    site_id TEXT NOT NULL,
    site_name TEXT NOT NULL,
    status TEXT NOT NULL,
    connected BOOLEAN NOT NULL DEFAULT TRUE,
    mqtt_connected BOOLEAN NOT NULL DEFAULT TRUE,
    spool_depth INTEGER NOT NULL DEFAULT 0,
    kafka_lag INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (updated_at, site_id)
);
SELECT create_hypertable('site_health', by_range('updated_at'), if_not_exists => TRUE);

CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_1m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 minute', ts_source) AS bucket,
    site_id,
    asset_id,
    signal_id,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value
FROM measurements
GROUP BY bucket, site_id, asset_id, signal_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_15m
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('15 minutes', ts_source) AS bucket,
    site_id,
    asset_id,
    signal_id,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value
FROM measurements
GROUP BY bucket, site_id, asset_id, signal_id;

CREATE MATERIALIZED VIEW IF NOT EXISTS measurements_1h
WITH (timescaledb.continuous) AS
SELECT
    time_bucket('1 hour', ts_source) AS bucket,
    site_id,
    asset_id,
    signal_id,
    avg(value) AS avg_value,
    min(value) AS min_value,
    max(value) AS max_value
FROM measurements
GROUP BY bucket, site_id, asset_id, signal_id;

