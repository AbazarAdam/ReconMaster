import requests
import json

BASE_URL = "http://127.0.0.1:8000"

def test_clear_history():
    print("Testing Clear History API...")
    try:
        # First, check if there are any scans
        r = requests.get(f"{BASE_URL}/api/scans")
        print(f"Current scans: {len(r.json())}")
        
        # Clear history
        print("Sending clear request...")
        r = requests.post(f"{BASE_URL}/api/scans/clear")
        print(f"Response: {r.status_code} - {r.json()}")
        
        # Verify empty
        r = requests.get(f"{BASE_URL}/api/scans")
        count = len(r.json())
        print(f"Scans after clear: {count}")
        
        if count == 0:
            print("[OK] Clear History works!")
        else:
            print("[FAIL] History not cleared.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_clear_history()
