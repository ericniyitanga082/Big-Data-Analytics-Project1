# Location: src/regional_normalization.py
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

def analyze_normalized_profiles():
    print("[*] Connecting to database on port 5434 for independent normalization...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # Query A: Independent Aggregation by Geographic Region
    region_query = """
        SELECT 
            m.region,
            SUM(r.energy_kwh) AS total_energy_kwh,
            COUNT(DISTINCT m.meter_id) AS registered_meter_count,
            SUM(r.energy_kwh) / COUNT(DISTINCT m.meter_id) AS energy_per_meter
        FROM energy_readings r
        JOIN meters m ON r.meter_id = m.meter_id
        GROUP BY m.region
        ORDER BY energy_per_meter DESC;
    """
    
    # Query B: Independent Aggregation by Customer Type
    customer_query = """
        SELECT 
            m.customer_type,
            SUM(r.energy_kwh) AS total_energy_kwh,
            COUNT(DISTINCT m.meter_id) AS registered_meter_count,
            SUM(r.energy_kwh) / COUNT(DISTINCT m.meter_id) AS energy_per_meter
        FROM energy_readings r
        JOIN meters m ON r.meter_id = m.meter_id
        GROUP BY m.customer_type
        ORDER BY energy_per_meter DESC;
    """
    
    print("[*] Gathering regional normalization profiles...")
    cursor.execute(region_query)
    region_results = cursor.fetchall()
    
    print("[*] Gathering customer segment normalization profiles...")
    cursor.execute(customer_query)
    customer_results = cursor.fetchall()
    
    # --- DISPLAY METRICS MATRIX REPORTS ---
    print("\n" + "="*80)
    print("=== SECTION 5.2: INDEPENDENT ANALYSIS BY GEOGRAPHIC REGION ===")
    print("="*80)
    print(f"{'Region Name':<20}{'Total Energy (kWh)':<22}{'Meter Count':<16}{'Energy Per Meter'}")
    print("-" * 80)
    for row in region_results:
        print(f"{row[0]:<20}{row[1]:<22,.2f}{row[2]:<16}{row[3]:,.2f} kWh")
        
    print("\n" + "="*80)
    print("=== SECTION 5.2: INDEPENDENT ANALYSIS BY CUSTOMER SEGMENT TYPE ===")
    print("="*80)
    print(f"{'Customer Type':<20}{'Total Energy (kWh)':<22}{'Meter Count':<16}{'Energy Per Meter'}")
    print("-" * 80)
    for row in customer_results:
        print(f"{row[0]:<20}{row[1]:<22,.2f}{row[2]:<16}{row[3]:,.2f} kWh")
    print("="*80)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    analyze_normalized_profiles()
