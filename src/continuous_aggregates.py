# Location: src/continuous_aggregates.py
import sys
import os
import time
import psycopg2
import psycopg2.extensions

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

def setup_continuous_aggregates():
    print("[*] Connecting to database on port 5434 for view deployment...")
    conn = psycopg2.connect(**DB_PARAMS)
    
    # Enable autocommit mode to prevent implicit transaction blocks for refresh operations
    conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
    cursor = conn.cursor()
    
    # 1. Drop existing views if they exist to allow clean retries
    cursor.execute("DROP MATERIALIZED VIEW IF EXISTS grid_agg_15min CASCADE;")
    cursor.execute("DROP MATERIALIZED VIEW IF EXISTS grid_agg_hourly CASCADE;")
    cursor.execute("DROP MATERIALIZED VIEW IF EXISTS grid_agg_daily CASCADE;")

    # Definitions layout matching specifications exactly
    views_ddl = {
        "grid_agg_15min": """
            CREATE MATERIALIZED VIEW grid_agg_15min
            WITH (timescaledb.continuous, timescaledb.materialized_only = true) AS
            SELECT 
                time_bucket(INTERVAL '15 minutes', r.event_time) AS bucket,
                m.region,
                SUM(r.energy_kwh) AS total_energy_kwh,
                SUM(r.power_kw) AS total_power_kw,
                COUNT(*) AS reading_count
            FROM energy_readings r
            INNER JOIN meters m ON r.meter_id = m.meter_id
            GROUP BY bucket, m.region WITH NO DATA;
        """,
        "grid_agg_hourly": """
            CREATE MATERIALIZED VIEW grid_agg_hourly
            WITH (timescaledb.continuous, timescaledb.materialized_only = true) AS
            SELECT 
                time_bucket(INTERVAL '1 hour', r.event_time) AS bucket,
                m.region,
                SUM(r.energy_kwh) AS total_energy_kwh,
                SUM(r.power_kw) AS total_power_kw,
                COUNT(*) AS reading_count
            FROM energy_readings r
            INNER JOIN meters m ON r.meter_id = m.meter_id
            GROUP BY bucket, m.region WITH NO DATA;
        """,
        "grid_agg_daily": """
            CREATE MATERIALIZED VIEW grid_agg_daily
            WITH (timescaledb.continuous, timescaledb.materialized_only = true) AS
            SELECT 
                time_bucket(INTERVAL '1 day', r.event_time) AS bucket,
                r.meter_id,
                SUM(r.energy_kwh) AS total_energy_kwh,
                SUM(r.power_kw) AS total_power_kw,
                COUNT(*) AS reading_count
            FROM energy_readings r
            GROUP BY bucket, r.meter_id WITH NO DATA;
        """
    }

    print("[*] Creating continuous aggregate structures (initially unpopulated)...")
    for name, ddl in views_ddl.items():
        cursor.execute(ddl)
        print(f"  [+] View definition applied: {name}")

    # 2. Manually Refresh the Entire Generated Period (September 2026 bounds)
    print("\n[*] Commencing historical data block manual materialization...")
    print("-" * 80)
    
    refresh_ranges = ("2026-09-01 00:00:00+02", "2026-09-30 00:00:00+02")
    
    for name in views_ddl.keys():
        t_start = time.time()
        cursor.execute(f"CALL refresh_continuous_aggregate('{name}', %s, %s);", refresh_ranges)
        t_duration = time.time() - t_start
        print(f"  [+] Materialization complete for view: {name:<16} | Duration: {t_duration:.2f} seconds")

    # 3. Audit Storage Sizes Footprints
    print("\n" + "=" * 80)
    print("=== SECTION 6.1: MATERIALIZED VIEW STORAGE METRICS ===")
    print("=" * 80)
    for name in views_ddl.keys():
        cursor.execute(f"""
            SELECT pg_size_pretty(pg_relation_size('{name}')) AS data_size,
                   pg_size_pretty(pg_total_relation_size('{name}') - pg_relation_size('{name}')) AS total_size;
        """)
        data_sz, tot_sz = cursor.fetchone()
        
        cursor.execute(f"SELECT COUNT(*) FROM {name};")
        row_count = cursor.fetchone()
        
        # CRITICAL FIX: Extract index 0 from the tuple objects before string width formatting
        print(f"View: {name:<16} | Materialized Rows: {row_count[0]:<8,} | Data Sz: {data_sz[0]:<8} | Total Sz: {tot_sz[0]}")
    print("=" * 80)

    # 4. Apply Automated Policies (3-day lookback, 1-hour end offset, 15-minute schedule)
    print("\n[*] Deploying active background automation policies...")
    for name in views_ddl.keys():
        cursor.execute(f"""
            SELECT add_continuous_aggregate_policy('{name}',
                start_offset => INTERVAL '3 days',
                end_offset => INTERVAL '1 hour',
                schedule_interval => INTERVAL '15 minutes',
                if_not_exists => true);
        """)
        print(f"  [+] Automation scheduler job applied for: {name}")

    # Verify active background scheduler status from jobs catalog
    print("\n" + "=" * 80)
    print("=== BACKGROUND JOB MONITOR RUNTIME CHECK ===")
    print("=" * 80)
    cursor.execute("""
        SELECT job_id, application_name, schedule_interval, scheduled 
        FROM timescaledb_information.jobs
        WHERE application_name LIKE '%Continuous Aggregate%';
    """)
    jobs = cursor.fetchall()
    for j in jobs:
        print(f"Job ID: {j[0]:<5} | Application: {j[1]:<35} | Schedule: {str(j[2]):<12} | Active: {j[3]}")
    print("=" * 80)

    cursor.close()
    conn.close()

if __name__ == "__main__":
    setup_continuous_aggregates()
