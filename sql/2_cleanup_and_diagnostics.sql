-- Location: sql/2_cleanup_and_diagnostics.sql
-- Section 2.2: Initial Structural Diagnostic Validation Queries
SELECT COUNT(*) AS total_raw_records_ingested FROM energy_readings;

SELECT 
    MIN(event_time) AS earliest_reading_timestamp,
    MAX(event_time) AS latest_reading_timestamp 
FROM energy_readings;

-- Section 2.3: Transaction-Isolated Data Cleanup & Deduplication Routine
BEGIN;

-- Generate isolated holding buffer with unique constraints, preserving the first arrival record
CREATE TEMP TABLE unique_readings_buffer AS
SELECT DISTINCT ON (event_time, meter_id) *
FROM energy_readings
ORDER BY event_time, meter_id, received_time ASC;

-- Truncate raw hypertable partition storage blocks
TRUNCATE TABLE energy_readings;

-- Stream deduplicated rows back into production storage partitions
INSERT INTO energy_readings 
SELECT * FROM unique_readings_buffer;

COMMIT;

-- Post-Cleaning Validation Checks
SELECT COUNT(*) AS total_cleaned_records_retained FROM energy_readings;
