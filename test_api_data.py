import sqlite3
import json

def test_api_data():
    conn = sqlite3.connect('recon.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    
    # Check screenshots
    print("\n--- Screenshot Data Samples ---")
    rows = c.execute("SELECT * FROM results WHERE type='screenshot' LIMIT 2").fetchall()
    for row in rows:
        data = json.loads(row['data'])
        print(f"Record from module {row['module']}:")
        print(json.dumps(data, indent=2))

    # Check vulns
    print("\n--- Vuln Data Samples ---")
    rows = c.execute("SELECT * FROM results WHERE type IN ('shodan', 'github', 'cloud_buckets', 'cloud_bucket') LIMIT 2").fetchall()
    for row in rows:
        data = json.loads(row['data'])
        print(f"Record from module {row['module']} (type: {row['type']}):")
        print(json.dumps(data, indent=2))
        
    conn.close()

if __name__ == "__main__":
    test_api_data()
