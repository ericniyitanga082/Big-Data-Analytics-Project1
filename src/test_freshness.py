# Location: src/test_freshness.py
import sys
import os
import psycopg2
import psycopg2.extensions
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

# Explicit time buckets formatted as standardized ISO strings
OLDER_HOUR_STR = "2026-10-13 23:00:00+02:00"
HOUR_H_STR       = "2026-10-15 23:00:00+02:00"

# Parse the reference strings into native datetime objects to match the database driver's format
OLDER_HOUR_KEY = datetime.fromisoformat(OLDER_HOUR_STR)
HOUR_H_KEY     = datetime.fromisoformat(HOUR_H_STR)

# Test row data timestamps placed inside the active hour buckets
T1_OLDER = "2026-10-13 23:10:00+02"  # 1.0 kWh
T2_OLDER = "2026-10-13 23:25:00+02"  # 0.5 kWh
T3_H     = "2026-10-15 23:10:00+02"  # 2.0 kWh

def query_agg_stage(cursor, stage_label):
    """Queries the aggregate view and maps keys using native datetime formatting."""
    cursor.execute("SELECT bucket, total_energy_kwh, reading_count FROM test_hourly_agg;")
    rows = cursor.fetchall()
    
    # Initialize dictionary using native datetime keys
    status = {OLDER_HOUR_KEY: "No bucket returned", HOUR_H_KEY: "No bucket returned"}
    
    for b, kwh, cnt in rows:
        # Check if the returned bucket object matches our reference keys
        if b in status:
            status[b] = f"{kwh:.1f} kWh, {cnt} row{'s' if cnt > 1 else ''}"
        
    print(f"| {stage_label:<46} | {status[OLDER_HOUR_KEY]:<20} | {status[HOUR_H_KEY]:<20} |")

def run_freshness_experiment():
    print("[*] Connecting to database on port 5434 in autocommit mode...")
    conn = psycopg2.connect(**DB_PARAMS)
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # 1. Reinitialize clean isolated environment structures
    cursor.execute("DROP MATERIALIZED VIEW IF EXISTS test_hourly_agg CASCADE;")
    cursor.execute("DROP TABLE IF EXISTS energy_test CASCADE;")
    
    cursor.execute("""
        CREATE TABLE energy_test (
            event_time TIMESTAMPTZ NOT NULL,
            energy_kwh DOUBLE PRECISION NOT NULL
        );
    """)
    cursor.execute("SELECT create_hypertable('energy_test', 'event_time');")
    
    # Initialize view with real-time aggregation disabled (materialized_only = true)
    cursor.execute("""
        CREATE MATERIALIZED VIEW test_hourly_agg
        WITH (timescaledb.continuous, timescaledb.materialized_only = true) AS
        SELECT 
            time_bucket(INTERVAL '1 hour', event_time) AS bucket,
            SUM(energy_kwh) AS total_energy_kwh,
            COUNT(*) AS reading_count
        FROM energy_test
        GROUP BY bucket WITH NO DATA;
    """)
    
    print("\n" + "="*97)
    print("--- SECTION 6.2: EXPERIMENTAL FRESHNESS AND DELAYED ARRIVALS TRANSITION MATRIX ---")
    print("="*97)
    print(f"| {'Measurement Experiment Stage':<46} | {'Older Hour Aggregate':<20} | {'Hour H Aggregate':<20} |")
    print("-" * 97)
    
    # --- STAGE 1: First insert into older hour + refresh only older hour (Real-Time OFF) ---
    cursor.execute("INSERT INTO energy_test VALUES (%s, 1.0);", (T1_OLDER,))
    cursor.execute("CALL refresh_continuous_aggregate('test_hourly_agg', '2026-10-13 23:00:00+02', '2026-10-14 01:00:00+02');")
    query_agg_stage(cursor, "Initial older-hour refresh, real-time off")
    
    # --- STAGE 2: Insert late data into older hour and hour H before refresh (Real-Time OFF) ---
    cursor.execute("INSERT INTO energy_test VALUES (%s, 0.5);", (T2_OLDER,))
    cursor.execute("INSERT INTO energy_test VALUES (%s, 2.0);", (T3_H,))
    query_agg_stage(cursor, "After both new inserts, before refresh, real-time off")
    
    # --- STAGE 3: Activate real-time dynamic aggregation ---
    cursor.execute("ALTER MATERIALIZED VIEW test_hourly_agg SET (timescaledb.materialized_only = false);")
    query_agg_stage(cursor, "Real-time on, still before refresh")
    
    # --- STAGE 4: Deactivate real-time mode and execute a comprehensive manual refresh ---
    cursor.execute("ALTER MATERIALIZED VIEW test_hourly_agg SET (timescaledb.materialized_only = true);")
    cursor.execute("CALL refresh_continuous_aggregate('test_hourly_agg', '2026-10-13 00:00:00+02', '2026-10-16 05:00:00+02');")
    query_agg_stage(cursor, "After manual refresh of both hours")
    
    print("="*97)
    
    # Final database validation integrity check
    cursor.execute("SELECT COUNT(*), SUM(energy_kwh) FROM energy_test;")
    raw_cnt, raw_sum = cursor.fetchone()
    print(f"\n[+] Raw Table Integrity Check: Total Records = {raw_cnt} | Cumulative Sum = {raw_sum:.1f} kWh")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_freshness_experiment()
