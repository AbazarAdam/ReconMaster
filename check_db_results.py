import sqlite3
import json

def check_db():
    try:
        conn = sqlite3.connect("recon.db")
        cursor = conn.cursor()
        
        print("--- [ Database Summary ] ---")
        
        # Check Scans
        cursor.execute("SELECT id, target, status FROM scans ORDER BY start_time DESC LIMIT 5")
        scans = cursor.fetchall()
        print(f"\nRecent Scans ({len(scans)} total):")
        for s in scans:
            print(f"  ID: {s[0]} | Target: {s[1]} | Status: {s[2]}")
            
        # Check Results count by scan_id
        cursor.execute("SELECT scan_id, type, COUNT(*) FROM results GROUP BY scan_id, type")
        counts = cursor.fetchall()
        print("\nResults by Scan ID and Type:")
        for c in counts:
            print(f"  Scan: {c[0]} | Type: {c[1]} | Count: {c[2]}")
            
        # Sample results with scan_id
        cursor.execute("SELECT target, module, type, scan_id FROM results ORDER BY id DESC LIMIT 5")
        samples = cursor.fetchall()
        print("\nRecent Sample Data:")
        for s in samples:
            print(f"  Target: {s[0]} | Module: {s[1]} | Type: {s[2]} | Scan: {s[3]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_db()
