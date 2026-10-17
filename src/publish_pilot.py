# Location: src/publish_pilot.py
import sys
import os
import json
import time
import paho.mqtt.client as mqtt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import smart_meter_simulator

generator_count = 0
acked_count = 0

def on_publish(client, userdata, mid):
    global acked_count
    acked_count += 1
    if acked_count % 200 == 0 or acked_count == 2000:
        print(f"[+] Broker Acknowledgment (QoS 1) Received Count: {acked_count}")

if __name__ == "__main__":
    client = mqtt.Client()
    client.on_publish = on_publish
    
    print("[*] Spawning publisher connection to EMQX container...")
    client.connect("127.0.0.1", 1883, 60)
    client.loop_start()

    print("[*] Streaming pipeline reading loops launched...")
    readings_iterator = smart_meter_simulator.iter_readings()
    
    for _ in range(2000):
        try:
            record = next(readings_iterator)
            generator_count += 1
            
            topic = f"energy/meters/{record['meter_id']}"
            payload_str = json.dumps(record)
            
            # Publish via explicit QoS 1 tracking parameters
            client.publish(topic, payload=payload_str, qos=1, retain=False)
            
        except StopIteration:
            print("[-] Data stream ended prematurely.")
            break

    # Hold window open for flight acknowledgments
    while acked_count < generator_count:
        time.sleep(0.1)

    client.loop_stop()
    client.disconnect()
    
    print("\n================================================================")
    print(f"[+] SIMULATOR STREAM COMPLETE")
    print(f"[+] Records Emitted: {generator_count}")
    print(f"[+] Network QoS 1 Acks: {acked_count}")
    print("================================================================")
