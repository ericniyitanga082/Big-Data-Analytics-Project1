-- Location: sql/3_continuous_aggregates.sql
-- Section 6.1: 15-Minute Regional Sum View Configuration
CREATE MATERIALIZED VIEW IF NOT EXISTS grid_agg_15min
WITH (timescaledb.continuous, timescaledb.materialized_only = TRUE) AS
SELECT 
    time_bucket(INTERVAL '15 minutes', r.event_time) AS bucket,
    m.region,
    SUM(r.energy_kwh) AS total_energy_kwh,
    SUM(r.power_kw) AS total_power_kw,
    COUNT(*) AS reading_count
FROM energy_readings r
INNER JOIN meters m ON r.meter_id = m.meter_id
GROUP BY bucket, m.region;

-- Section 6.1: Hourly Regional Sum View Configuration
CREATE MATERIALIZED VIEW IF NOT EXISTS grid_agg_hourly
WITH (timescaledb.continuous, timescaledb.materialized_only = TRUE) AS
SELECT 
    time_bucket(INTERVAL '1 hour', r.event_time) AS bucket,
    m.region,
    SUM(r.energy_kwh) AS total_energy_kwh,
    SUM(r.power_kw) AS total_power_kw,
    COUNT(*) AS reading_count
FROM energy_readings r
INNER JOIN meters m ON r.meter_id = m.meter_id
GROUP BY bucket, m.region;

-- Section 6.1: Daily Per-Meter Node View Configuration
CREATE MATERIALIZED VIEW IF NOT EXISTS grid_agg_daily
WITH (timescaledb.continuous, timescaledb.materialized_only = TRUE) AS
SELECT 
    time_bucket(INTERVAL '1 day', r.event_time) AS bucket,
    r.meter_id,
    SUM(r.energy_kwh) AS total_energy_kwh,
    SUM(r.power_kw) AS total_power_kw,
    COUNT(*) AS reading_count
FROM energy_readings r
GROUP BY bucket, r.meter_id;

-- Section 6.1: Active Automated Scheduler Refresh Policies Deployment
SELECT add_continuous_aggregate_policy('grid_agg_15min',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '15 minutes', if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('grid_agg_hourly',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '15 minutes', if_not_exists => TRUE);

SELECT add_continuous_aggregate_policy('grid_agg_daily',
    start_offset => INTERVAL '3 days', end_offset => INTERVAL '1 hour', schedule_interval => INTERVAL '15 minutes', if_not_exists => TRUE);
