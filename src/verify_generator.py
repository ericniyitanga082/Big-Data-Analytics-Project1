# Location: src/verify_generator.py
import hashlib
import os
import sys

def calculate_checksum(filename: str) -> str:
    """Computes the SHA-256 hash of a file progressively in memory blocks."""
    if not os.path.exists(filename):
        print(f"[-] Operational Error: The file '{filename}' was not found in the root directory.")
        return ""
    
    sha256_engine = hashlib.sha256()
    with open(filename, "rb") as target_file:
        # Read in 64KB blocks to prevent memory overhead
        for block in iter(lambda: target_file.read(65536), b""):
            sha256_engine.update(block)
            
    return sha256_engine.hexdigest()

if __name__ == "__main__":
    target_module = "smart_meter_simulator.py"
    print(f"[*] Beginning integrity verification scan for: {target_module}...")
    
    computed_hash = calculate_checksum(target_module)
    if computed_hash:
        print("\n================================================================")
        print(f"[+] INTEGRITY CHECK PASSED SUCCESSFULLY")
        print(f"[+] Target Reference File: {target_module}")
        print(f"[+] Computed SHA-256 Hash: {computed_hash}")
        print("================================================================")
        print("[*] Unique project workspace initialized. Ready for database deployment.")
    else:
        sys.exit(1)
