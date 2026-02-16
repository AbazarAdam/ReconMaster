import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000"

def test_scan_progress():
    print("Starting scan for google.com...")
    try:
        r = requests.post(f"{BASE_URL}/api/scans", json={"target": "google.com"})
        scan_id = r.json()["scan_id"]
        print(f"Scan ID: {scan_id}")
        
        # Monitor for 60 seconds
        for _ in range(30):
            time.sleep(2)
            r = requests.get(f"{BASE_URL}/api/scans/{scan_id}")
            status = r.json()
            print(f"[{time.strftime('%H:%M:%S')}] Status: {status['status']}")
            
            if status['status'] == 'completed':
                print("Scan completed successfully!")
                break
            if status['status'] == 'failed':
                print("Scan failed!")
                break
                
            # Check results so far
            res = requests.get(f"{BASE_URL}/api/targets/google.com/results")
            print(f"      - Findings: {len(res.json())}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_scan_progress()
