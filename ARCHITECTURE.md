# ReconMaster Architecture

![ReconMaster Architecture Diagram](architecture.png)

## Overview

ReconMaster is a modular, asynchronous OSINT automation platform for cybersecurity reconnaissance. It features a CLI, web dashboard, REST API, and real-time updates via WebSockets.

### Key Components
- **core/engine.py**: Orchestrates scans, loads config, manages modules, and coordinates results.
- **core/database.py**: Handles result storage and retrieval (SQLite).
- **core/rate_limiter.py**: Global async token bucket for API and network rate limiting.
- **core/proxy_manager.py**: Manages HTTP/SOCKS proxies and Tor for all network requests.
- **modules/**: Pluggable modules for subdomain, portscan, HTTP, screenshots, Shodan, GitHub, and cloud buckets.
- **web/**: FastAPI app, REST API, WebSocket manager, and Jinja2 templates for the dashboard.

### Data Flow
1. User starts a scan (CLI or Web UI)
2. Engine loads config, initializes DB, rate limiter, and proxy
3. Modules run in parallel phases, storing results in DB
4. Web UI shows live progress via WebSocket
5. Results are browsable in the dashboard and via API

---

## Extending ReconMaster
- Add new modules in `modules/` (inherit from `BaseModule`)
- Register in `config/default.yaml` under `modules.enabled`
- Results are automatically stored and shown in the dashboard

---

## Challenges & Solutions
- **Async orchestration**: Used asyncio and careful locking for concurrency
- **Rate limiting**: Global token bucket to avoid bans
- **Proxy support**: aiohttp-socks for Tor and HTTP proxies
- **WebSockets**: Real-time updates for a responsive UI
- **Dockerization**: Multi-stage build, .env for secrets, volume mounts for persistence

---

For more, see the [README.md](README.md) and [DEMO_VIDEO.md](DEMO_VIDEO.md).
