# ReconMaster

An advanced OSINT automation tool for reconnaissance, subdomain discovery, and enriched service intelligence.

## Phase 3 Features
- Parallel module execution with phase-based dependencies
- Global rate limiting and optional proxy/Tor support
- Shodan enrichment for IPs and services
- GitHub dorking for exposed code and secrets
- Cloud bucket enumeration (AWS, Azure, GCP)
- Deduplication helpers for cleaner results

## Requirements
- Python 3.10+ (verified with Python 3.14 for asyncio)
- Optional: Playwright browsers for screenshots

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Playwright browsers (for screenshots):
   ```bash
   playwright install
   ```

## Configuration
Edit config/default.yaml to enable modules and set keys, rate limits, and proxies.

Example highlights:
```yaml
api_keys:
  shodan: ""
  github: ""

rate_limit: 10
proxy:
  http: ""
  https: ""
  use_tor: false

modules:
  enabled:
    subdomain: ["ct", "alienvault", "anubis", "virustotal", "securitytrails"]
    portscan: ["scanner"]
    http: ["detector"]
    screenshot: ["capturer"]
    shodan: ["enricher"]
    github: ["dorker"]
    cloud_buckets: ["enumerator"]
```

Notes:
- Shodan and GitHub modules skip gracefully if API keys are missing.
- SOCKS proxies (including Tor) are supported via aiohttp-socks.

## Run a Scan
```bash
python main.py scanme.nmap.org
```

Results are stored in recon.db, and screenshots (if enabled) are saved under reports/screenshots.

## Phase 3 Verification
- Ensure config/default.yaml is updated with your keys and desired modules.
- Run the scan and confirm module outputs in recon.db.
- Review recon.log for module progress and rate limit behavior.

---

## Phase 4: Web Dashboard & REST API

ReconMaster now includes a web interface and REST API for managing scans, viewing live progress, and browsing results.

### Features
- Web dashboard (FastAPI + Bootstrap) to start scans, view progress, and see results
- REST API for programmatic scan management and result retrieval
- Live progress updates via WebSockets
- Docker and docker-compose support for easy deployment

### Quick Start (Web UI)
1. Install new dependencies:
  ```bash
  pip install -r requirements.txt
  playwright install
  ```
2. Start the web server:
  ```bash
  uvicorn web.app:app --host 0.0.0.0 --port 8000
  ```
3. Open [http://localhost:8000](http://localhost:8000) in your browser.

### Using Docker
Build and run with Docker Compose:
```bash
docker-compose up --build
```
The web dashboard will be available at [http://localhost:8000](http://localhost:8000).

### REST API Endpoints
- `POST /api/scans` – Start a new scan (JSON: `{ "target": "example.com" }`)
- `GET /api/scans` – List all scans
- `GET /api/scans/{scan_id}` – Get scan details
- `GET /api/scans/{scan_id}/results` – Get results for a scan
- `GET /api/targets/{target}/results` – Get all results for a target
- `DELETE /api/scans/{scan_id}` – Cancel a running scan

### Live Progress
WebSocket endpoint: `/ws/{scan_id}` streams real-time scan progress to the dashboard.

### Configuration
Edit `config/default.yaml` to set web server host, port, and secret key:
```yaml
web:
  host: "0.0.0.0"
  port: 8000
  debug: false
  secret_key: "change-this-in-production"
```

---
For more details, see walkthrough.md and task.md for step-by-step usage and development notes.
