# Location: src/clean_benchmark.py
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

def clean_and_benchmark():
    print("[*] Connecting to database on port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # 1. Capture Pre-Cleaning Benchmark Metrics
    print("[*] Gathering baseline metrics before data cleaning...")
    cursor.execute("SELECT COUNT(*), SUM(energy_kwh) FROM energy_readings;")
    pre_count, pre_sum = cursor.fetchone()
    
    # 2. Check for Conflicting Values
    # This query finds duplicate pairs that have different values in their data columns
    print("[*] Checking for conflicting metrics in duplicate records...")
    conflict_query = """
        SELECT COUNT(*) FROM (
            SELECT meter_id, event_time
            FROM energy_readings
            GROUP BY meter_id, event_time
            HAVING COUNT(DISTINCT (received_time, power_kw, voltage_v, current_a, frequency_hz, energy_kwh)) > 1
        ) AS conflicts;
    """
    cursor.execute(conflict_query)
    conflicts_count = cursor.fetchone()[0]
    
    # 3. Perform Deduplication Transaction Block
    start_time = time.time()
    print(f"[*] Found {conflicts_count} conflicting records. Executing clean deduplication...")
    
    dedup_sql = """
        BEGIN;
        
        -- Extract one row per unique pair, keeping the one with the earliest received_time
        CREATE TEMP TABLE temp_deduplicated_readings AS
        SELECT DISTINCT ON (meter_id, event_time)
            meter_id, event_time, received_time, power_kw, voltage_v, current_a, frequency_hz, energy_kwh
        FROM energy_readings
        ORDER BY meter_id, event_time, received_time ASC;
        
        -- Truncate master hypertable to clear uncleaned rows
        TRUNCATE TABLE energy_readings;
        
        -- Re-inject the cleaned rows
        INSERT INTO energy_readings SELECT * FROM temp_deduplicated_readings;
        
        COMMIT;
    """
    cursor.execute(dedup_sql)
    conn.commit()
    
    end_time = time.time()
    elapsed = end_time - start_time
    
    # 4. Capture Post-Cleaning Benchmark Metrics
    cursor.execute("SELECT COUNT(*), SUM(energy_kwh) FROM energy_readings;")
    post_count, post_sum = cursor.fetchone()
    
    print("\n================================================================")
    print("=== SECTION 2.3: DATA DEDUPLICATION BENCHMARK REPORT ===")
    print("================================================================")
    print(f"[+] Total Conflicting Pairs Found:   {conflicts_count}")
    print(f"[+] Cleaning Transaction Duration:   {elapsed:.2f} seconds")
    print("-" * 64)
    print(f"[+] Row Count BEFORE Cleaning:       {pre_count:,}")
    print(f"[+] Row Count AFTER Cleaning:        {post_count:,} (Expected: 10,643,735)")
    print(f"[+] Total Rows Removed:              {pre_count - post_count:,}")
    print("-" * 64)
    print(f"[+] Total Energy Sum BEFORE Clean:   {pre_sum:.4f} kWh")
    print(f"[+] Total Energy Sum AFTER Clean:    {post_sum:.4f} kWh")
    print(f"[+] Mathematical Energy Variance:    {abs(pre_sum - post_sum):.4f} kWh")
    print("================================================================")
    
    if post_count == 10643735:
        print("[===] SUCCESS: ROW COUNT MATCHES EXPECTED UNIQUE READINGS METRIC [===]")
    else:
        print("[-] WARNING: Mismatch detected in final row count.")
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    clean_and_benchmark()
