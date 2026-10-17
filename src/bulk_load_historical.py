# Location: src/bulk_load_historical.py
import sys
import os
import time
import io
import psycopg2

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import smart_meter_simulator

# Connection settings matching your active D-drive container port binding
DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

BATCH_BLOCK_SIZE = 100000  # Stream buffer block size (100k rows per flush)

def execute_historical_bulk_load():
    print("[*] Opening high-speed connection channel on database port 5434...")
    conn = psycopg2.connect(**DB_PARAMS)
    cursor = conn.cursor()
    
    print("[*] Truncating table 'energy_readings' to ensure a clean benchmark run...")
    cursor.execute("TRUNCATE TABLE energy_readings;")
    conn.commit()
    
    print("[*] Fetching target metric details from dataset inspector...")
    dataset_metadata = smart_meter_simulator.dataset_info()
    expected_rows = dataset_metadata["expected_counts"]["emitted_readings"]
    print(f"[+] Total target records to process: {expected_rows}")
    
    print("[*] Opening active data generator stream iterator...")
    stream_iterator = smart_meter_simulator.iter_readings()
    
    processed_count = 0
    string_buffer = io.StringIO()
    
    # Start execution clock timer
    start_timestamp = time.time()
    
    print("[*] Ingestion pipeline running. Streaming data blocks...")
    for record in stream_iterator:
        # Convert dictionary values into a tab-delimited text row format
        row_line = f"{record['meter_id']}\t{record['event_time']}\t{record['received_time']}\t{record['power_kw']}\t{record['voltage_v']}\t{record['current_a']}\t{record['frequency_hz']}\t{record['energy_kwh']}\n"
        string_buffer.write(row_line)
        processed_count += 1
        
        # When chunk matches block size constraint, flush to database via COPY protocol
        if processed_count % BATCH_BLOCK_SIZE == 0:
            string_buffer.seek(0)
            cursor.copy_from(string_buffer, 'energy_readings', sep='\t', 
                             columns=('meter_id', 'event_time', 'received_time', 'power_kw', 'voltage_v', 'current_a', 'frequency_hz', 'energy_kwh'))
            conn.commit()
            string_buffer = io.StringIO()  # Clear buffer memory allocations
            print(f"[-] Data Engine Tracking: Buffered and pushed {processed_count} rows...")

    # Flush any remaining rows left in the buffer
    if processed_count % BATCH_BLOCK_SIZE != 0:
        string_buffer.seek(0)
        cursor.copy_from(string_buffer, 'energy_readings', sep='\t', 
                         columns=('meter_id', 'event_time', 'received_time', 'power_kw', 'voltage_v', 'current_a', 'frequency_hz', 'energy_kwh'))
        conn.commit()
        
    end_timestamp = time.time()
    total_elapsed_seconds = end_timestamp - start_timestamp
    
    # Query database engine row storage directly for absolute confirmation
    cursor.execute("SELECT COUNT(*) FROM energy_readings;")
    confirmed_db_rows = cursor.fetchone()[0]
    
    print("\n================================================================")
    print("=== HIGH-SPEED BULK LOAD PIPELINE PERFORMANCE SUMMARY ===")
    print("================================================================")
    print(f"[+] Total Iterated Stream Records: {processed_count}")
    print(f"[+] Verified Database Table Rows:   {confirmed_db_rows}")
    print(f"[+] Total Processing Duration:     {total_elapsed_seconds:.2f} seconds")
    print(f"[+] Ingestion Pipeline Throughput: {processed_count / total_elapsed_seconds:.2f} rows/sec")
    print("================================================================")
    
    if confirmed_db_rows == expected_rows:
        print("[===] SUCCESS: DATA PLATFORM VERIFICATION PROFILES MATCH EXPECTED TOTALS [===]")
    else:
        print("[-] WARNING: Row count mismatch detected. Please review pipeline logs.")
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    execute_historical_bulk_load()
