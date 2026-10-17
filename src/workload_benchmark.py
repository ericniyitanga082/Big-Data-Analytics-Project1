# Location: src/workload_benchmark.py
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

# SQL Queries dictionary matching specifications exactly
QUERIES = {
    "Q1": """
        SELECT EXTRACT(HOUR FROM event_time) AS cat_hour, AVG(power_kw) AS avg_power 
        FROM {table} 
        WHERE event_time >= '2026-09-21 00:00:00+02' AND event_time < '2026-09-22 00:00:00+02'
        GROUP BY cat_hour ORDER BY cat_hour;
    """,
    "Q2": """
        SELECT event_time, SUM(power_kw) AS total_power 
        FROM {table} 
        WHERE event_time >= '2026-09-22 00:00:00+02' AND event_time <= '2026-09-28 23:45:00+02'
        GROUP BY event_time 
        ORDER BY total_power DESC, event_time ASC 
        LIMIT 10;
    """,
    "Q3": """
        SELECT meter_id, SUM(energy_kwh) AS lifetime_energy 
        FROM {table} 
        GROUP BY meter_id;
    """,
    "Q4": """
        SELECT SUM(energy_kwh) AS total_energy, AVG(power_kw) AS avg_power, MAX(power_kw) AS max_power 
        FROM {table} 
        WHERE meter_id = 1000000000 AND event_time >= '2026-09-22 00:00:00+02' AND event_time <= '2026-09-28 23:45:00+02';
    """,
    "Q5": """
        SELECT COUNT(*), SUM(energy_kwh), AVG(power_kw), MIN(power_kw), MAX(power_kw) 
        FROM {table};
    """
}

def benchmark_workloads():
    print("[*] Opening analytical session channel on port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    tables = ['energy_readings_3h', 'energy_readings', 'energy_readings_week']
    results_matrix = {q: {t: [] for t in tables} for q in QUERIES}
    
    session_start = time.time()
    
    for q_name, sql_template in QUERIES.items():
        print(f"\n==================== PROCESSING WORKLOAD: {q_name} ====================")
        for t_name in tables:
            query = sql_template.format(table=t_name)
            
            # 1. Warm-up Execution (Unmeasured)
            cursor.execute(query)
            cursor.fetchall()
            
            # 2. Measured Iterations (5 Runs)
            for i in range(5):
                start_t = time.time()
                cursor.execute(query)
                cursor.fetchall()
                end_t = time.time()
                
                latency_ms = (end_t - start_t) * 1000
                results_matrix[q_name][t_name].append(latency_ms)
            
            print(f"[+] Cleaned table profile: {t_name:<20} Done.")

    session_duration = time.time() - session_start
    
    # 3. Print Final Academic Metrics Summary Report
    print("\n" + "="*80)
    print("=== SECTION 3.2: GRAND WORKLOAD PERFORMANCE METRICS COMPARISON MATRIX ===")
    print("="*80)
    print(f"{'Workload':<10}{'Hypertable Target':<22}{'Min (ms)':<14}{'Max (ms)':<14}{'Median (ms)':<14}")
    print("-" * 80)
    
    for q_name in QUERIES:
        for t_name in tables:
            latencies = results_matrix[q_name][t_name]
            min_l = min(latencies)
            max_l = max(latencies)
            med_l = statistics.median(latencies)
            print(f"{q_name:<10}{t_name:<22}{min_l:<14.2f}{max_l:<14.2f}{med_l:<14.2f}")
        print("-" * 80)
        
    print(f"[+] Client Environment Machine Identifier: LOCAL_HOST_WIN_CMD")
    print(f"[+] Total Benchmark Session Runtime:     {session_duration:.2f} seconds")
    print("="*80)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    benchmark_workloads()
