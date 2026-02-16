import requests
import time
import json
import sys

BASE_URL = "http://127.0.0.1:8000"
TARGET = "google.com"

def test_full_scan_flow():
    print(f"--- [ Full Scan Flow Verification ] ---")
    
    # 1. Start Scan
    print(f"Starting scan for {TARGET}...")
    try:
        r = requests.post(f"{BASE_URL}/api/scans", json={"target": TARGET})
        if r.status_code != 201:
            print(f"[FAIL] Failed to start scan: {r.status_code} - {r.text}")
            return
        
        scan_data = r.json()
        scan_id = scan_data["scan_id"]
        print(f"[OK] Scan started. ID: {scan_id}")
        
        # 2. Wait and Monitor Status
        print("Monitoring scan status (waiting for completion)...")
        max_retries = 30 # 2 minutes roughly
        completed = False
        
        for i in range(max_retries):
            r = requests.get(f"{BASE_URL}/api/scans/{scan_id}")
            status_data = r.json()
            status = status_data.get("status")
            print(f"[{i+1}/{max_retries}] Status: {status}")
            
            if status in ["completed", "failed"]:
                completed = True
                break
            time.sleep(10)
            
        if not completed:
            print("[FAIL] Scan timed out or did not reach final state.")
            return
            
        # 3. Verify Results
        print("\nFetching results for this scan_id...")
        r = requests.get(f"{BASE_URL}/api/scans/{scan_id}/results")
        results = r.json()
        
        print(f"Found {len(results)} total results linked to scan_id {scan_id}")
        
        counts = {}
        for res in results:
            t = res.get("type")
            counts[t] = counts.get(t, 0) + 1
            
        print("Result Breakdown:")
        for t, c in counts.items():
            print(f"  - {t}: {c}")
            
        if len(results) > 0:
            print(f"\n[SUCCESS] Results successfully stored and retrieved for scan_id {scan_id}!")
        else:
            print(f"\n[FAIL] No results found for scan_id {scan_id} even though scan is {status}.")

    except Exception as e:
        print(f"Error during test: {e}")

if __name__ == "__main__":
    test_full_scan_flow()
