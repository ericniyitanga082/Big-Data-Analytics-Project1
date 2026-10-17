# Location: src/consume_pilot.py
import sys
import os
import json
import psycopg2
import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

DB_PARAMS = {
    "host": "127.0.0.1",
    "port": 5434,
    "user": "postgres",
    "password": "postgres_secret_pass",
    "database": "auca_energy_db"
}

received_count = 0

def on_connect(client, userdata, flags, rc):
    print(f"[+] Subscriber connected to broker with result code {rc}")
    client.subscribe("energy/meters/#", qos=1)
    print("[*] Active subscription on topic energy/meters/# at QoS 1. Awaiting stream...")

def on_message(client, userdata, msg):
    global received_count
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        
        conn = psycopg2.connect(**DB_PARAMS)
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO energy_live (
                meter_id, event_time, received_time, power_kw, 
                voltage_v, current_a, frequency_hz, energy_kwh
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s);
        """
        
        cursor.execute(insert_query, (
            payload["meter_id"],
            payload["event_time"],
            payload["received_time"],
            payload["power_kw"],
            payload["voltage_v"],
            payload["current_a"],
            payload["frequency_hz"],
            payload["energy_kwh"]
        ))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        received_count += 1
        if received_count % 200 == 0 or received_count == 2000:
            print(f"[-] Pipeline Storage Status: Committed {received_count} live records.")
            
        if received_count >= 2000:
            print(f"[===] TARGET REACHED: Total pipeline consumer rows saved: {received_count} [===]")
            client.disconnect()
            
    except Exception as e:
        print(f"[-] Data entry execution error: {e}")

if __name__ == "__main__":
    # Clean staging table before test run
    conn = psycopg2.connect(**DB_PARAMS)
    c = conn.cursor()
    c.execute("TRUNCATE TABLE energy_live;")
    conn.commit()
    c.close()
    conn.close()
    print("[*] Table 'energy_live' truncated successfully.")

    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect("127.0.0.1", 1883, 60)
    client.loop_forever()
