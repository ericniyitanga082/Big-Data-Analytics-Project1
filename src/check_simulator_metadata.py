# Location: src/check_simulator_metadata.py
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import smart_meter_simulator

def audit_simulator_specs():
    print("[*] Interrogating smart_meter_simulator dataset_info()...")
    info = smart_meter_simulator.dataset_info()
    
    print("\n================================================================")
    print("=== METADATA REFERENCE SPECIFICATIONS INSIDE SIMULATOR ===")
    print("================================================================")
    print(f"[+] Total Planned Readings: {info.get('planned_readings', 'N/A')}")
    
    expected_counts = info.get("expected_counts", {})
    print("\nExpected Counts Structure:")
    for key, val in expected_counts.items():
        print(f"  [-] {key}: {val}")
    print("================================================================")

if __name__ == "__main__":
    audit_simulator_specs();
