import sqlite3
import json

def check_db():
    conn = sqlite3.connect('recon.db')
    cursor = conn.cursor()
    
    print("--- Database Screenshot Check ---")
    cursor.execute("SELECT id, target, scan_id, data FROM results WHERE type='screenshot' ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    
    if not rows:
        print("No screenshot results found in recon.db.")
    else:
        print(f"Found {len(rows)} screenshot results:")
        for row in rows:
            print(f"ID: {row[0]}, Target: {row[1]}, ScanID: {row[2]}")
            data = json.loads(row[3])
            print(f"  Data: {data}")
            
    conn.close()

if __name__ == "__main__":
    check_db()
