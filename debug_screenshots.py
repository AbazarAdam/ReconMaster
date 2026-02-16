import sqlite3
import json
import os
import sys

def check_playwright():
    try:
        from playwright.async_api import async_playwright
        print("✅ Playwright Python package is installed.")
        return True
    except ImportError:
        print("❌ Playwright Python package is NOT installed.")
        return False

def check_db():
    print("\n--- Database Check ---")
    try:
        conn = sqlite3.connect('recon.db')
        c = conn.cursor()
        rows = c.execute("SELECT target, data FROM results WHERE type='screenshot'").fetchall()
        print(f"Found {len(rows)} screenshot records in database.")
        for target, data_str in rows:
            data = json.loads(data_str)
            print(f"Target: {target}")
            if isinstance(data, list):
                for item in data:
                    print(f"  - {item}")
            else:
                print(f"  - {data}")
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

def check_files():
    print("\n--- Filesystem Check ---")
    screenshot_dir = "reports/screenshots"
    if os.path.exists(screenshot_dir):
        files = os.listdir(screenshot_dir)
        print(f"Directory {screenshot_dir} exists and contains {len(files)} files:")
        for f in files:
            print(f"  - {f}")
    else:
        print(f"❌ Directory {screenshot_dir} does NOT exist.")

if __name__ == "__main__":
    check_playwright()
    check_db()
    check_files()
