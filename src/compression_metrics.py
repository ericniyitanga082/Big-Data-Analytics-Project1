# Location: src/compression_metrics.py
import sys
import os
import time
import statistics
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

def analyze_compression_metrics():
    print("[*] Connecting to database on port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # 1. SECTION 4.2: Storage Size Footprint Extraction
    print("[*] Retrieving physical disk space metrics...")
    size_query = """
        SELECT 
            pg_size_pretty(table_bytes) AS data_sz,
            pg_size_pretty(index_bytes) AS index_sz,
            pg_size_pretty(total_bytes) AS total_sz,
            total_bytes
        FROM hypertable_detailed_size('{table_name}');
    """
    
    tables = ['energy_readings', 'energy_time_compressed', 'energy_meter_compressed']
    storage_stats = {}
    
    for t in tables:
        cursor.execute(size_query.format(table_name=t))
        data_sz, index_sz, total_sz, raw_bytes = cursor.fetchone()
        storage_stats[t] = {'data': data_sz, 'index': index_sz, 'total': total_sz, 'bytes': raw_bytes}

    print("\n========================================================================")
    print("=== SECTION 4.2: DETAILED STORAGE FOOTPRINT SIZE METRICS ===")
    print("========================================================================")
    for t in tables:
        print(f"Table: {t:<25} | Data: {storage_stats[t]['data']:<10} | Index: {storage_stats[t]['index']:<10} | Combined: {storage_stats[t]['total']}")
    
    # Calculate exact mathematical savings ratio
    base_bytes = storage_stats['energy_readings']['bytes']
    time_ratio = base_bytes / storage_stats['energy_time_compressed']['bytes']
    meter_ratio = base_bytes / storage_stats['energy_meter_compressed']['bytes']
    
    print("-" * 72)
    print(f"[+] Time-Ordered Compression Space Savings Ratio:  {time_ratio:.2f}x smaller")
    print(f"[+] Meter-Segmented Compression Space Savings Ratio: {meter_ratio:.2f}x smaller")
    print("========================================================================")
    
    # 2. SECTION 4.3: Query Performance Latency Benchmark (Workload Q1)
    query_template = """
        SELECT EXTRACT(HOUR FROM event_time) AS cat_hour, AVG(power_kw) AS avg_power 
        FROM {table_name} 
        WHERE event_time >= '2026-09-21 00:00:00+02' AND event_time < '2026-09-22 00:00:00+02'
        GROUP BY cat_hour ORDER BY cat_hour;
    """
    
    print("\n[*] Launching performance latency benchmarks (5 iterations + warm-up)...")
    benchmark_results = {t: [] for t in tables}
    
    for t in tables:
        query = query_template.format(table_name=t)
        # Warm-up run
        cursor.execute(query)
        cursor.fetchall()
        
        for i in range(5):
            start_t = time.time()
            cursor.execute(query)
            cursor.fetchall()
            end_t = time.time()
            benchmark_results[t].append((end_t - start_t) * 1000)
            
    print("\n========================================================================")
    print("=== SECTION 4.3: COMPRESSED CONFIGURATION LATENCY MATRIX ===")
    print("========================================================================")
    print(f"{'Hypertable Configuration':<28}{'Median Latency (ms)':<25}")
    print("-" * 65)
    for t in tables:
        median_lat = statistics.median(benchmark_results[t])
        print(f"{t:<28}{median_lat:>18.2f} ms")
    print("========================================================================")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    analyze_compression_metrics()
