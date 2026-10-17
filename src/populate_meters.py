# Location: src/populate_meters.py
import sys
import os
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import smart_meter_simulator

# Structured database connection parameters matching port 5434 host routing bindings
DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

def load_meter_metadata():
    print("[*] Connecting to database on host port 5434...")
    try:
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        print("[*] Retrieving metadata dictionaries from generator stream...")
        meta_records = smart_meter_simulator.meter_metadata()
        
        insert_statement = """
            INSERT INTO meters (meter_id, region, customer_type, base_power_kw, power_factor)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (meter_id) DO NOTHING;
        """
        
        batch_data = [
            (
                item["meter_id"],
                item["region"],
                item["customer_type"],
                item["base_power_kw"],
                item["power_factor"]
            )
            for item in meta_records
        ]
        
        print(f"[*] Executing high-speed batch append for {len(batch_data)} records...")
        cursor.executemany(insert_statement, batch_data)
        conn.commit()
        
        # Verify committed row counts inside table
        cursor.execute("SELECT COUNT(*) FROM meters;")
        final_count = cursor.fetchone()[0]
        print(f"[+] Validation Check: 'meters' table row count is: {final_count}")
        
        cursor.close()
        conn.close()
        print("[+] Metadata population routine successfully finalized.")
        
    except Exception as error:
        print(f"[-] Operational Failure during metadata ingestion: {error}")
        sys.exit(1)

if __name__ == "__main__":
    load_meter_metadata()
