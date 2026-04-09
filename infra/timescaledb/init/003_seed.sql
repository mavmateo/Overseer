INSERT INTO asset_registry (asset_id, site_id, area_id, name, protocol)
VALUES
    ('crusher-01', 'site-alpha', 'processing', 'Primary Crusher 01', 'mqtt'),
    ('pump-07', 'site-alpha', 'dewatering', 'Dewatering Pump 07', 'mqtt'),
    ('tank-02', 'site-alpha', 'storage', 'Storage Tank 02', 'mqtt'),
    ('gasdet-04', 'site-alpha', 'utilities', 'Gas Detector 04', 'mqtt')
ON CONFLICT (asset_id) DO NOTHING;

INSERT INTO signal_registry (asset_id, signal_id, unit, sampling_class)
VALUES
    ('crusher-01', 'motor_current', 'A', '1s'),
    ('crusher-01', 'bearing_temp', 'C', '5s'),
    ('crusher-01', 'vibration_rms', 'mm/s', '1s'),
    ('pump-07', 'discharge_pressure', 'bar', '1s'),
    ('pump-07', 'flow_rate', 'm3/h', '1s'),
    ('tank-02', 'level', '%', '5s'),
    ('gasdet-04', 'h2s_ppm', 'ppm', '1s')
ON CONFLICT (asset_id, signal_id) DO NOTHING;

INSERT INTO site_health (updated_at, site_id, site_name, status, connected, mqtt_connected, spool_depth, kafka_lag)
VALUES (NOW(), 'site-alpha', 'Site Alpha', 'connected', TRUE, TRUE, 0, 0)
ON CONFLICT DO NOTHING;

