# Location: src/compare_groups.py
import sys
import os
import time
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

def setup_and_verify_chunks():
    print("[*] Connecting to database on port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # 1. Create schemas and hypertables with transactional safety
    print("[*] Generating 3-Hour and 1-Week hypertables...")
    ddl_sql = """
    BEGIN;
    -- Drop tables if they exist to allow clean retries
    DROP TABLE IF EXISTS energy_readings_3h CASCADE;
    DROP TABLE IF EXISTS energy_readings_week CASCADE;

    -- Create 3-Hour table structure
    CREATE TABLE energy_readings_3h (LIKE energy_readings INCLUDING DEFAULTS);
    SELECT create_hypertable('energy_readings_3h', 'event_time', chunk_time_interval => INTERVAL '3 hours', if_not_exists => TRUE);

    -- Create 1-Week table structure
    CREATE TABLE energy_readings_week (LIKE energy_readings INCLUDING DEFAULTS);
    SELECT create_hypertable('energy_readings_week', 'event_time', chunk_time_interval => INTERVAL '7 days', if_not_exists => TRUE);
    COMMIT;
    """
    cursor.execute(ddl_sql)
    conn.commit()

    # 2. Populate new hypertables directly from the clean master dataset
    print("[*] Migrating 10.6M+ clean records to energy_readings_3h (This takes a moment)...")
    t0 = time.time()
    cursor.execute("INSERT INTO energy_readings_3h SELECT * FROM energy_readings;")
    conn.commit()
    print(f"[+] 3-Hour table populated in {time.time() - t0:.2f} seconds.")

    print("[*] Migrating 10.6M+ clean records to energy_readings_week...")
    t0 = time.time()
    cursor.execute("INSERT INTO energy_readings_week SELECT * FROM energy_readings;")
    conn.commit()
    print(f"[+] 1-Week table populated in {time.time() - t0:.2f} seconds.")

    # 3. Apply identical matching indexes
    print("[*] Building performance indexes across structures...")
    index_sql = """
    BEGIN;
    -- Indexes for 1-day (ensure they exist)
    CREATE INDEX IF NOT EXISTS idx_readings_time ON energy_readings(event_time DESC);
    CREATE INDEX IF NOT EXISTS idx_readings_meter_time ON energy_readings(meter_id, event_time DESC);

    -- Indexes for 3-hour
    CREATE INDEX idx_readings_3h_time ON energy_readings_3h(event_time DESC);
    CREATE INDEX idx_readings_3h_meter_time ON energy_readings_3h(meter_id, event_time DESC);

    -- Indexes for 1-week
    CREATE INDEX idx_readings_week_time ON energy_readings_week(event_time DESC);
    CREATE INDEX idx_readings_week_meter_time ON energy_readings_week(meter_id, event_time DESC);
    COMMIT;
    """
    cursor.execute(index_sql)
    conn.commit()
    print("[+] All indexes successfully applied.")

    # 4. Perform Data Integrity Checks across configurations
    tables = ['energy_readings', 'energy_readings_3h', 'energy_readings_week']
    metrics = {}

    print("[*] Executing structural audit across hypertable profiles...")
    for t in tables:
        # Get count, sums, bounds
        cursor.execute(f"""
            SELECT COUNT(*), COUNT(DISTINCT meter_id), MIN(event_time), MAX(event_time), 
                   SUM(power_kw), SUM(energy_kwh) 
            FROM {t};
        """)
        row_cnt, meter_cnt, min_t, max_t, sum_p, sum_e = cursor.fetchone()
        
        # Get actual chunk count from timescaledb information view
        cursor.execute(f"SELECT COUNT(*) FROM timescaledb_information.chunks WHERE hypertable_name = '{t}';")
        chunk_cnt = cursor.fetchone()[0]
        
        metrics[t] = {
            'rows': row_cnt, 'meters': meter_cnt, 'min': min_t, 'max': max_t,
            'sum_power': float(sum_p), 'sum_energy': float(sum_e), 'chunks': chunk_cnt
        }

    # Print out comparison reports
    print("\n========================================================================")
    print("=== SECTION 3.1: MULTI-CONFIGURATION HYPERTABLE VERIFICATION ===")
    print("========================================================================")
    for t, data in metrics.items():
        print(f"\n[+] Hypertable Configuration Target: {t}")
        print(f"  [-] Total Physical Chunks Created: {data['chunks']}")
        print(f"  [-] Row Count Verification:       {data['rows']:,} (Expected: 10,643,735)")
        print(f"  [-] Unique Smart Meter Nodes:    {data['meters']}")
        print(f"  [-] Time Boundary Windows:        {data['min']} --> {data['max']}")
        print(f"  [-] Combined power_kw Aggregates: {data['sum_power']:.3f}")
        print(f"  [-] Combined energy_kwh Aggregate: {data['sum_energy']:.3f}")
    print("========================================================================")

    # Cross validation check
    row_check = (metrics['energy_readings']['rows'] == metrics['energy_readings_3h']['rows'] == metrics['energy_readings_week']['rows'] == 10643735)
    print(f"\n[===] DATA MATRIX SYNCHRONIZATION QUALITY: {'PASSED' if row_check else 'FAILED'} [===]")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    setup_and_verify_chunks()
