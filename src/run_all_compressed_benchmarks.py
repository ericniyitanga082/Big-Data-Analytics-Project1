# Location: src/run_all_compressed_benchmarks.py
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

# Empirical baseline medians from Section 3.2 uncompressed 1-day table
BASELINE_MEDIANS = {"Q1": 167.35, "Q2": 283.67, "Q3": 1220.75, "Q4": 1.61, "Q5": 622.33}
# Other baseline references for the grand report matrix display
UNCOMP_3H_MEDIANS = {"Q1": 126.09, "Q2": 286.76, "Q3": 31034.41, "Q4": 4.75, "Q5": 860.08}
# Updated dynamically or referenced from past run
UNCOMP_WEEK_MEDIANS = {"Q1": 286.08, "Q2": 540.05, "Q3": 437.09, "Q4": 1.32, "Q5": 570.00}

QUERIES = {
    "Q1": "SELECT EXTRACT(HOUR FROM event_time) AS hr, AVG(power_kw) FROM {table} WHERE event_time >= '2026-09-21 00:00:00+02' AND event_time < '2026-09-22 00:00:00+02' GROUP BY hr ORDER BY hr;",
    "Q2": "SELECT event_time, SUM(power_kw) AS tot FROM {table} WHERE event_time >= '2026-09-22 00:00:00+02' AND event_time <= '2026-09-28 23:45:00+02' GROUP BY event_time ORDER BY tot DESC LIMIT 10;",
    "Q3": "SELECT meter_id, SUM(energy_kwh) FROM {table} GROUP BY meter_id;",
    "Q4": "SELECT SUM(energy_kwh), AVG(power_kw) FROM {table} WHERE meter_id = 1000000000 AND event_time >= '2026-09-22 00:00:00+02' AND event_time <= '2026-09-28 23:45:00+02';",
    "Q5": "SELECT COUNT(*), SUM(energy_kwh), AVG(power_kw) FROM {table};"
}

def run_grand_comparison():
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    comp_tables = ['energy_time_compressed', 'energy_meter_compressed']
    medians = {q: {t: 0.0 for t in comp_tables} for q in QUERIES}
    
    print("[*] Running benchmarks on compressed configurations (Q1 - Q5)...")
    for q_name, sql in QUERIES.items():
        for t_name in comp_tables:
            query = sql.format(table=t_name)
            # Warm up
            cursor.execute(query)
            cursor.fetchall()
            
            runs = []
            for _ in range(5):
                t_start = time.time()
                cursor.execute(query)
                cursor.fetchall()
                runs.append((time.time() - t_start) * 1000)
            medians[q_name][t_name] = statistics.median(runs)

    print("\n" + "="*115)
    print("=== SECTION 4.3: FIVE-CONFIGURATION GRAND LATENCY METRICS COMPARISON MATRIX (ms) ===")
    print("="*115)
    print(f"{'Job':<6}{'Uncomp 3H':<14}{'Uncomp 1D':<14}{'Uncomp 1W':<14}{'Time Compressed':<20}{'Meter Compressed':<20}")
    print("-" * 115)
    
    for q in QUERIES:
        t_comp = medians[q]['energy_time_compressed']
        m_comp = medians[q]['energy_meter_compressed']
        base = BASELINE_MEDIANS[q]
        
        # Calculate percentage improvements: 100 * (baseline - compressed) / baseline
        t_imp = 100.0 * (base - t_comp) / base
        m_imp = 100.0 * (base - m_comp) / base
        
        print(f"{q:<6}{UNCOMP_3H_MEDIANS[q]:<14.2f}{base:<14.2f}{UNCOMP_WEEK_MEDIANS[q]:<14.2f}"
              f"{t_comp:<8.2f} ({t_imp:>5.1f}%){m_comp:<8.2f} ({m_imp:>5.1f}%)")
    print("="*115)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_grand_comparison()
