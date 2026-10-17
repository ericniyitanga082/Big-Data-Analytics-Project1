-- Location: sql/1_schema.sql
-- Section 1.1: Environment Initialization
CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;

-- Create Dimensional Metadata Table
CREATE TABLE IF NOT EXISTS meters (
    meter_id BIGINT PRIMARY KEY,
    region VARCHAR(50) NOT NULL,
    customer_type VARCHAR(50) NOT NULL
);

-- Create Time-Series Hypertable Root Table
CREATE TABLE IF NOT EXISTS energy_readings (
    event_time TIMESTAMPTZ NOT NULL,
    meter_id BIGINT NOT NULL,
    power_kw DOUBLE PRECISION NOT NULL,
    voltage_v DOUBLE PRECISION NOT NULL,
    current_a DOUBLE PRECISION NOT NULL,
    energy_kwh DOUBLE PRECISION NOT NULL,
    received_time TIMESTAMPTZ NOT NULL,
    CONSTRAINT fk_meter FOREIGN KEY (meter_id) REFERENCES meters(meter_id)
);

-- Section 1.2: Hypertable Transformation (1-Day Space-Time Split Interval)
SELECT create_hypertable('energy_readings', 'event_time', if_not_exists => TRUE);

-- Create Custom Performance Optimization Indexes
CREATE INDEX IF NOT EXISTS idx_meters_lookup_cover ON meters(region, customer_type);
CREATE INDEX IF NOT EXISTS idx_readings_covering_search ON energy_readings(meter_id, event_time DESC, energy_kwh);
