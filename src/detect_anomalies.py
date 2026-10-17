# Location: src/detect_anomalies.py
import sys
import os
import psycopg2
from datetime import datetime

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import smart_meter_simulator

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

def parse_to_naive_datetime(dt_input):
    """Converts input string or datetime object into a naive datetime structure."""
    if isinstance(dt_input, str):
        # Handle trailing Z or timezone offsets by splitting or replacing
        clean_str = dt_input.replace('Z', '').split('+')[0]
        return datetime.fromisoformat(clean_str)
    elif hasattr(dt_input, 'tzinfo'):
        return dt_input.replace(tzinfo=None)
    return dt_input

def run_anomaly_investigation():
    print("[*] Connecting to database on port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # 1. Define Rule Thresholds and Reasons
    # Rule Strategy: Volumetric Limit paired with Voltage Sag detection.
    # Thresholds: voltage_v < 207.0 V OR power_kw > 12.5 kW.
    print("[*] Executing anomaly detection rule query over cleaned readings...")
    rule_query = """
        SELECT meter_id, event_time, power_kw, voltage_v, current_a
        FROM energy_readings
        WHERE voltage_v < 207.0 OR power_kw > 12.5
        ORDER BY meter_id, event_time ASC;
    """
    cursor.execute(rule_query)
    flagged_rows = cursor.fetchall()
    print(f"[+] Rule processing complete. Total anomalous intervals flagged: {len(flagged_rows):,}")
    
    # Map flags into dictionaries for efficient lookups
    flagged_map = {}
    for r in flagged_rows:
        m_id = r[0]
        f_time = parse_to_naive_datetime(r[1])
        flagged_map.setdefault(m_id, []).append(f_time)
        
    # 2. Sourcing the 40 Injected Ground-Truth Events
    print("[*] Loading ground-truth injected intervals from simulator...")
    injected_events = smart_meter_simulator.anomaly_events()
    
    detected_events_count = 0
    missed_events_count = 0
    
    # Validate each injected event against our flags map
    for event in injected_events:
        m_id = event["meter_id"]
        start = parse_to_naive_datetime(event["start_time"])
        end = parse_to_naive_datetime(event["end_time"])
        
        is_detected = False
        if m_id in flagged_map:
            for f_time in flagged_map[m_id]:
                if start <= f_time < end:
                    is_detected = True
                    break
        
        if is_detected:
            detected_events_count += 1
        else:
            missed_events_count += 1
            
    # 3. Calculate False Alarms
    print("[*] Performing spatial overlap analysis to calculate false flags...")
    false_flags_count = 0
    meters_with_false_flags = set()
    
    for m_id, f_times in flagged_map.items():
        m_injections = [e for e in injected_events if e["meter_id"] == m_id]
        for f_time in f_times:
            inside_injection = False
            for inj in m_injections:
                start_inj = parse_to_naive_datetime(inj["start_time"])
                end_inj = parse_to_naive_datetime(inj["end_time"])
                
                if start_inj <= f_time < end_inj:
                    inside_injection = True
                    break
            if not inside_injection:
                false_flags_count += 1
                meters_with_false_flags.add(m_id)
                
    # Calculate denominators precisely
    print("[*] Counting total baseline readings residing outside injected intervals...")
    cursor.execute("SELECT COUNT(*) FROM energy_readings;")
    total_clean_rows = cursor.fetchone()[0]
    
    total_rows_inside_injections = 40 * 16
    total_readings_outside_intervals = total_clean_rows - total_rows_inside_injections
    
    # Calculate percentage metrics
    pct_false_flags = (false_flags_count / total_readings_outside_intervals) * 100
    pct_meters_affected = (len(meters_with_false_flags) / 4000.0) * 100
    
    # --- PRINT OUT VISUAL AUDIT MATRIX ---
    print("\n" + "="*85)
    print("=== SECTION 5.4: ABNORMAL CONSUMPTION SCORING RESULTS ===")
    print("="*85)
    print(f"[+] Configured Detection Thresholds:      [voltage_v < 207.0V OR power_kw > 12.5kW]")
    print(f"[+] Total Labeled Injected Events:        40")
    print(f"[+] Successfully Detected Events:         {detected_events_count} / 40")
    print(f"[+] Missed Injected Events (Escaped):     {missed_events_count} / 40")
    print("-" * 85)
    print(f"[+] Raw Count of False Flags:             {false_flags_count:,} readings")
    print(f"[+] Percentage of False Flags:            {pct_false_flags:.5f}%")
    print(f"[+] Unique Meters with False Flags:       {len(meters_with_false_flags)}")
    print(f"[+] Percentage of Meters Affected:        {pct_meters_affected:.2f}%")
    print("="*85)
    
    # Print sample logs for report verification
    print("\n[#] SAMPLE OUTPUT OF DETECTED FLAGGED READINGS:")
    print("-" * 75)
    print(f"{'Meter ID':<15}{'Event Time (CAT)':<30}{'Power (kW)':<12}{'Voltage (V)'}")
    print("-" * 75)
    for row in flagged_rows[:5]:
        print(f"{row[0]:<15}{str(row[1]):<30}{row[2]:<12.2f}{row[3]:.2f} V")
    print("="*85)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    run_anomaly_investigation()
