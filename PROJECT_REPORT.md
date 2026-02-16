# ReconMaster – Full Project Report

## Overview
ReconMaster is an advanced, modular OSINT automation framework for reconnaissance, subdomain discovery, and enriched service intelligence. It is designed for security professionals, bug bounty hunters, and researchers who need a scalable, extensible, and automated recon platform.

---

## Features
- **Parallel Module Execution:** True concurrency using asyncio for fast, scalable scans.
- **Global Rate Limiting:** Token bucket rate limiter for polite, configurable scraping.
- **Proxy & Tor Support:** Anonymity via HTTP/SOCKS proxies and Tor integration.
- **Shodan Enrichment:** Integrates Shodan API for port/service intelligence.
- **GitHub Dorking:** Finds exposed code, secrets, and credentials via GitHub code search.
- **Cloud Bucket Enumeration:** Detects open AWS S3, Azure Blob, and GCP buckets.
- **Deduplication & Filtering:** Intelligent result deduplication and false positive reduction.
- **Web Dashboard:** FastAPI-based web UI for scan management, live progress, and results.
- **REST API:** Programmatic scan control and result retrieval.
- **Live Progress Updates:** WebSocket-powered real-time scan status.
- **Dockerized:** Easy deployment with Docker and docker-compose.

---

## Project Structure
```
recon-master/
├── core/                # Core engine, config, database, utils, rate limiter, proxy
├── modules/             # Recon modules: subdomain, portscan, http, screenshot, shodan, github, cloud_buckets
├── web/                 # Web dashboard (FastAPI), API, WebSocket, templates, static
├── config/              # YAML configuration files
├── reports/             # Output: screenshots, logs, etc.
├── scripts/             # (Optional) Helper scripts
├── tests/               # (Optional) Test cases
├── requirements.txt     # Python dependencies
├── Dockerfile           # Docker build
├── docker-compose.yml   # Docker orchestration
├── README.md            # Main documentation
└── PROJECT_REPORT.md    # This report
```

---

## Core Components
### Engine (`core/engine.py`)
- Orchestrates module execution in parallel phases using `asyncio.gather()`.
- Handles dependency management between modules (e.g., Shodan after portscan).
- Accepts a `progress_callback` for real-time updates (used by web dashboard).

### Database (`core/database.py`)
- Stores all findings in SQLite (`recon.db`).
- Deduplication logic for unique results per target/module.
- Thread-safe access for web/API usage (via `asyncio.to_thread`).

### Rate Limiter & Proxy (`core/rate_limiter.py`, `core/proxy_manager.py`)
- Global async rate limiter for all HTTP requests.
- Proxy manager supports HTTP, HTTPS, SOCKS, and Tor.

### Utils (`core/utils.py`)
- Domain validation, extraction, deduplication helpers, robots.txt parsing.

---

## Modules
- **Subdomain:** Multiple sources (crt.sh, AlienVault, Anubis, VirusTotal, SecurityTrails).
- **Portscan:** Async TCP port scanning with configurable ports/concurrency.
- **HTTP:** Detects HTTP services, fetches headers, checks status.
- **Screenshot:** Captures screenshots of HTTP services (uses Playwright).
- **Shodan:** Enriches IPs with Shodan data (open ports, banners, vulns).
- **GitHub:** Dorks for secrets, keys, and code leaks using PyGithub.
- **Cloud Buckets:** Checks for open/public S3, Azure, and GCP buckets.

---

## Web Dashboard & API
- **Framework:** FastAPI (async, modern, OpenAPI docs)
- **Templates:** Jinja2 + Bootstrap 5 for UI
- **API:**
  - `POST /api/scans` – Start scan
  - `GET /api/scans` – List scans
  - `GET /api/scans/{scan_id}` – Scan details
  - `GET /api/scans/{scan_id}/results` – Results for scan
  - `GET /api/targets/{target}/results` – Results for target
  - `DELETE /api/scans/{scan_id}` – Cancel scan
- **WebSocket:** `/ws/{scan_id}` for live progress
- **Frontend:**
  - Start scans, view progress, browse results (with filtering/sorting)
  - Screenshots displayed as thumbnails

---

## Configuration
- All settings in `config/default.yaml`:
  - API keys, rate limits, proxy, enabled modules, web server settings
- Example:
```yaml
web:
  host: "0.0.0.0"
  port: 8000
  debug: false
  secret_key: "change-this-in-production"
```

---

## Installation & Usage
### Prerequisites
- Python 3.10+
- (Optional) Playwright browsers: `playwright install`
- (Optional) Docker & docker-compose

### Local Setup
```bash
pip install -r requirements.txt
playwright install
uvicorn web.app:app --host 0.0.0.0 --port 8000
```
Visit [http://localhost:8000](http://localhost:8000)

### Docker
```bash
docker-compose up --build
```

---

## Running a Scan (CLI)
```bash
python main.py scanme.nmap.org
```
Results in `recon.db` and `reports/screenshots/`.

---

## Running a Scan (Web)
- Go to dashboard, enter target, start scan.
- Watch live progress and view results.

---

## Security & Best Practices
- **API keys:** Store in `config/default.yaml` (never commit secrets to git!)
- **Proxy/Tor:** Use for anonymity if required.
- **Rate limits:** Respect targets' robots.txt and legal boundaries.
- **Production:** Change `secret_key` and use HTTPS in production.

---

## Extending ReconMaster
- Add new modules under `modules/` (inherit from BaseModule)
- Register in config and engine
- Use provided helpers for HTTP, rate limiting, and proxies

---

## Troubleshooting
- **Missing API keys:** Modules skip gracefully, but add keys for full results.
- **Screenshots fail:** Ensure Playwright browsers are installed.
- **Web UI not loading:** Check Docker logs or run `uvicorn` manually.
- **Database locked:** Avoid running too many concurrent scans; SQLite is file-based.

---

## Credits
- Built with FastAPI, aiohttp, Playwright, PyGithub, Shodan, and more.
- Inspired by the OSINT and bug bounty community.

---

## License
MIT License (see LICENSE file)
