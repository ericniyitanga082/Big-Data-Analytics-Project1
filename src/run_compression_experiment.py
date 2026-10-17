# Location: src/run_compression_experiment.py
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

def execute_compression_pipeline():
    print("[*] Opening high-performance session channel on database port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    # Define experiment boundary cut-off timestamp (Start minus 48 hours relative to final historical data tail)
    CUTOFF_TIMESTAMP = '2026-09-26 00:00:00+02'
    
    print("[*] Populating compressed configuration tables from cleaned master dataset...")
    cursor.execute("TRUNCATE TABLE energy_time_compressed; TRUNCATE TABLE energy_meter_compressed;")
    conn.commit()
    
    t0 = time.time()
    cursor.execute("INSERT INTO energy_time_compressed SELECT * FROM energy_readings;")
    cursor.execute("INSERT INTO energy_meter_compressed SELECT * FROM energy_readings;")
    conn.commit()
    print(f"[+] Initial layout population completed in {time.time() - t0:.2f} seconds.")
    
    # Retrieve all allocated chunk names from timescaledb internal information schemas
    cursor.execute("""
        SELECT chunk_name, range_end
        FROM timescaledb_information.chunks
        WHERE hypertable_name = 'energy_time_compressed'
        ORDER BY range_end ASC;
    """)
    chunks = cursor.fetchall()
    
    print(f"\n[*] Slicing and manually compressing chunks preceding experimental cutoff boundary: {CUTOFF_TIMESTAMP}")
    print("=" * 80)
    
    for chunk_name, range_end in chunks:
        # Cast range_end to text representation for clear comparison limits
        if str(range_end) < CUTOFF_TIMESTAMP:
            # Compress energy_time_compressed chunk partition
            t_start = time.time()
            cursor.execute(f"SELECT compress_chunk('_timescaledb_internal.{chunk_name}', if_not_compressed => TRUE);")
            conn.commit()
            t_duration = time.time() - t_start
            
            # Compress corresponding energy_meter_compressed chunk partition
            # Chunks share identical time slice ranges by design alignment
            cursor.execute(f"""
                SELECT chunk_name FROM timescaledb_information.chunks 
                WHERE hypertable_name = 'energy_meter_compressed' AND range_end = %s;
            """, (range_end,))
            meter_chunk_name = cursor.fetchone()[0]
            
            m_start = time.time()
            cursor.execute(f"SELECT compress_chunk('_timescaledb_internal.{meter_chunk_name}', if_not_compressed => TRUE);")
            conn.commit()
            m_duration = time.time() - m_start
            
            print(f"[+] Chunk End Boundary: {range_end} | Time-Comp Duration: {t_duration:.3f}s | Meter-Comp Duration: {m_duration:.3f}s")

    print("\n[*] Running cross-configuration data integrity check queries...")
    tables = ['energy_readings', 'energy_time_compressed', 'energy_meter_compressed']
    
    print("\n" + "=" * 80)
    print("=== SECTION 4.1: DATA MATRIX INTEGRITY MUTUAL CROSS-VALIDATION ===")
    print("=" * 80)
    for t in tables:
        cursor.execute(f"SELECT COUNT(*), SUM(energy_kwh) FROM {t};")
        count, energy_sum = cursor.fetchone()
        cursor.execute(f"SELECT COUNT(*) FROM timescaledb_information.chunks WHERE hypertable_name = '{t}';")
        chunks_count = cursor.fetchone()[0]
        
        cursor.execute(f"""
            SELECT COUNT(*) FROM timescaledb_information.chunks 
            WHERE hypertable_name = '{t}' AND is_compressed = True;
        """)
        compressed_count = cursor.fetchone()[0]
        
        print(f"Hypertable: {t:<25} | Total Rows: {count:,} | Chunks: {chunks_count} | Compressed: {compressed_count} | Energy Sum: {float(energy_sum):.4f}")
    print("=" * 80)
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    execute_compression_pipeline()
