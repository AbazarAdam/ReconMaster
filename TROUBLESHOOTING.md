# 🛠️ ReconMaster Troubleshooting Guide

This guide covers common issues and solutions for installing, running, and debugging ReconMaster.

---

## 1. Installation Issues

### ❌ "Module not found" or Import Errors
**Symptoms:** `ModuleNotFoundError: No module named 'fastapi'` or similar.
**Solution:**
Ensure you have installed all dependencies in your active environment:
```bash
pip install -r requirements.txt
```

### ❌ Playwright / Browser Errors
**Symptoms:** `playwright._impl._api_types.Error: Executable doesn't exist at ...`
**Solution:**
Playwright needs to download its browser binaries:
```bash
playwright install chromium
```
If that fails, try installing the system dependencies (Linux only):
```bash
playwright install-deps
```

---

## 2. Server Won't Start

### ❌ Port 8000 Already in Use
**Symptoms:** `ERROR: [Errno 10048] error while attempting to bind on address ('127.0.0.1', 8000)`
**Solution:**
A previous instance of the server is likely still running.
**Windows (PowerShell):**
```powershell
# Find the process ID (PID)
netstat -ano | findstr :8000
# Kill the process (replace <PID> with the actual number)
taskkill /PID <PID> /F
```
**Linux/Mac:**
```bash
lsof -i :8000
kill -9 <PID>
```

---

## 3. Database Errors

### ❌ "Database is locked"
**Symptoms:** `sqlite3.OperationalError: database is locked`
**Solution:**
This usually happens if a previous process crashed while holding a write lock.
1. Stop the server (`Ctrl+C`).
2. Ensure no zombie python processes are running.
3. Restart the server. Requesting WAL mode (Write-Ahead Logging) is handled automatically by the application to minimize this.

---

## 4. Scan & Screenshot Issues

### ❌ "Internal Server Error" on Scan Start
**Symptoms:** Clicking "Start Scan" shows an error popup or 500 status.
**Solution:**
This has been patched in the latest version (commit `3848c7c`+). Ensure you are running the latest code. If it persists:
1. clear the database history: `POST /api/scans/clear`
2. Restart the server.

### ❌ Screenshots Not Saving / Empty Images
**Symptoms:** Screenshots appear as broken images or "N/A".
**Solution:**
1. Verify Playwright is installed (`playwright install chromium`).
2. **Windows Path Issues**: Ensure the project path doesn't contain strict permissions or special characters.
3. Check `reports/screenshots/` permissions. The application must be able to write to this folder.

---

## 5. Module Failures

### ❌ "API Key Missing"
**Symptoms:** Modules like Shodan, GitHub, or SecurityTrails show "Skipped" or errors in logs.
**Solution:**
These modules require valid API keys in `config/secrets.yaml`.
1. Copy `config/secrets.example.yaml` to `config/secrets.yaml`.
2. Add your keys:
   ```yaml
   api_keys:
     shodan: "YOUR_KEY"
     github: "YOUR_KEY"
   ```

### ❌ Rate Limiting (429 Errors)
**Symptoms:** Logs show `[WARNING] API returned non-200 status: 429`.
**Solution:**
The engine automatically handles rate limits, but if you are scanning aggressively:
1. Edit `config/default.yaml`.
2. Reduce the global request rate or increase delays.

---

## 6. Getting Help

If you encounter an issue not listed here:
1. Check the logs in the terminal window for a Python traceback.
2. Open an issue on GitHub with the traceback and your environment details (OS, Python version).
