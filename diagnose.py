import os
import sys
import sqlite3
import logging
from pathlib import Path
import aiohttp
import asyncio
import subprocess

def check_env():
    print("--- [ Environment Check ] ---")
    print(f"Python Version: {sys.version}")
    print(f"Working Directory: {os.getcwd()}")
    
    # Check dependencies
    deps = ['fastapi', 'uvicorn', 'aiohttp', 'bs4', 'playwright']
    for dep in deps:
        try:
            __import__(dep)
            print(f"[OK] {dep} is installed")
        except ImportError:
            print(f"[FAIL] {dep} is NOT installed")

def check_db():
    print("\n--- [ Database Check ] ---")
    db_path = "recon.db"
    if not os.path.exists(db_path):
        print(f"[FAIL] {db_path} not found")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [t[0] for t in cursor.fetchall()]
        print(f"Tables found: {', '.join(tables)}")
        
        expected = ['results', 'scans']
        for t in expected:
            if t in tables:
                print(f"[OK] Table '{t}' exists")
                cursor.execute(f"SELECT COUNT(*) FROM {t}")
                count = cursor.fetchone()[0]
                print(f"      - Row count: {count}")
            else:
                print(f"[FAIL] Table '{t}' is MISSING")
        
        conn.close()
    except Exception as e:
        print(f"[FAIL] Database error: {e}")

def check_filesystem():
    print("\n--- [ Filesystem Check ] ---")
    paths = [
        "web/static",
        "web/templates",
        "reports",
        "reports/screenshots",
        "modules",
        "config"
    ]
    
    for p in paths:
        path = Path(p)
        if path.exists():
            status = "DIR" if path.is_dir() else "FILE"
            writeable = os.access(path, os.W_OK)
            print(f"[OK] {p} exists ({status}, Write: {'Yes' if writeable else 'No'})")
        else:
            print(f"[FAIL] {p} is MISSING")

async def check_playwright():
    print("\n--- [ Playwright Check ] ---")
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            print("[OK] Playwright library loaded")
            try:
                browser = await p.chromium.launch(headless=True)
                print("[OK] Chromium launched successfully")
                await browser.close()
            except Exception as e:
                print(f"[FAIL] Browser launch failed: {e}")
                print("      Tip: Run 'playwright install chromium'")
    except ImportError:
        print("[FAIL] Playwright NOT installed")

if __name__ == "__main__":
    check_env()
    check_db()
    check_filesystem()
    asyncio.run(check_playwright())
    print("\n--- [ Diagnosis Complete ] ---")
