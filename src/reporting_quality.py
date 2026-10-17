# Location: src/reporting_quality.py
import sys
import os
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

def execute_reporting_quality_assessment():
    print("[*] Connecting to database on port 5434 for quality analysis...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    PLANNED_PER_METER = 28 * 96
    TOTAL_PLANNED_NETWORK = 4000 * PLANNED_PER_METER
    
    # 1. Regional Data Completeness Query
    completeness_query = """
        SELECT 
            m.region,
            COUNT(DISTINCT m.meter_id) AS meter_count,
            COUNT(DISTINCT m.meter_id || '-' || r.event_time) AS observed_unique_pairs
        FROM meters m
        LEFT JOIN energy_readings r ON m.meter_id = r.meter_id
        GROUP BY m.region
        ORDER BY m.region ASC;
    """
    cursor.execute(completeness_query)
    regional_rows = cursor.fetchall()
    
    # 2. Extracting the Two Distinct Daily Totals for September 21
    sept_21_query = """
        SELECT 
            SUM(CASE WHEN r.received_time <= '2026-09-22 00:00:00+02' THEN r.energy_kwh ELSE 0 END) AS on_time_sum,
            SUM(r.energy_kwh) AS final_total_sum
        FROM energy_readings r
        WHERE r.event_time >= '2026-09-21 00:00:00+02' 
          AND r.event_time < '2026-09-22 00:00:00+02';
    """
    cursor.execute(sept_21_query)
    on_time_energy, final_total_energy = cursor.fetchone()
    
    on_time_energy = float(on_time_energy or 0.0)
    final_total_energy = float(final_total_energy or 0.0)
    absolute_diff_kwh = final_total_energy - on_time_energy
    variance_pct = (absolute_diff_kwh / final_total_energy) * 100 if final_total_energy > 0 else 0.0
    
    total_observed_network = sum(row[2] for row in regional_rows)
    global_completeness_pct = (total_observed_network / TOTAL_PLANNED_NETWORK) * 100
    
    # --- PRINT OUT FORMATTED CONSOLE REPORT ---
    print("\n" + "="*85)
    print("=== SECTION 5.3: STRUCTURAL TELEMETRY REPORTING QUALITY METRICS ===")
    print("="*85)
    print(f"{'Region':<15}{'Meters Count':<15}{'Observed Unique':<20}{'Completeness Rate'}")
    print("-" * 85)
    for row in regional_rows:
        region, meters, observed = row
        planned = meters * PLANNED_PER_METER
        comp_pct = (observed / planned) * 100
        print(f"{region:<15}{meters:<15}{observed:<20}{comp_pct:.4f}%")
        
    print("-" * 85)
    print(f"[+] Global Network-Wide Data Completeness Score: {global_completeness_pct:.4f}%")
    
    print("\n" + "="*85)
    print("=== EXPLICIT VERIFICATION OF THE TWO DAILY TOTALS (21 SEPTEMBER) ===")
    print("="*85)
    print(f"[1] DAILY TOTAL A (On-Time / Received by 22 Sep 00:00):  {on_time_energy:,.4f} kWh")
    print(f"[2] DAILY TOTAL B (Final Total / Including All Late):    {final_total_energy:,.4f} kWh")
    print("-" * 85)
    print(f"[+] Absolute Telemetric Delay Gap (Difference):          {absolute_diff_kwh:,.4f} kWh")
    print(f"[+] Relative Telemetric Impact Percentage:               {variance_pct:.4f}%")
    print("="*85)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    execute_reporting_quality_assessment()

