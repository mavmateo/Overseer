ALTER TABLE measurements SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'site_id,asset_id,signal_id'
);
SELECT add_compression_policy('measurements', INTERVAL '7 days', if_not_exists => TRUE);
SELECT add_retention_policy('measurements', INTERVAL '13 months', if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy(
    'measurements_1m',
    start_offset => INTERVAL '2 days',
    end_offset => INTERVAL '1 minute',
    schedule_interval => INTERVAL '5 minutes',
    if_not_exists => TRUE
);
SELECT add_continuous_aggregate_policy(
    'measurements_15m',
    start_offset => INTERVAL '14 days',
    end_offset => INTERVAL '15 minutes',
    schedule_interval => INTERVAL '15 minutes',
    if_not_exists => TRUE
);
SELECT add_continuous_aggregate_policy(
    'measurements_1h',
    start_offset => INTERVAL '90 days',
    end_offset => INTERVAL '1 hour',
    schedule_interval => INTERVAL '1 hour',
    if_not_exists => TRUE
);

