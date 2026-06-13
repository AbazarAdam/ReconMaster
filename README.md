# ReconMaster 🛡️

Advanced Automated Reconnaissance Framework for security professionals.

## 🚀 Overview
ReconMaster is a modular, high-performance reconnaissance tool designed to automate the discovery and enumeration phases of a security assessment. It provides a centralized dashboard for managing scans, viewing live progress, and analyzing results.
<img width="1059" height="621" alt="image" src="https://github.com/user-attachments/assets/c1fd8a59-4367-44a8-bedc-f270da5bcea1" />

## ✨ Features
- **Parallel Discovery**: Rapid subdomain enumeration and IP discovery.
- **Service Detection**: Automated port scanning and HTTP service identification.
- **Deep Artifact Collection**: Screenshot capturing, tech stack detection, and cloud bucket enumeration.
- **Modern UI**: High-contrast professional interface with live progress tracking and detailed reports.
- **Stealth & Resilience**: Integrated proxy rotation, rate limiting, and browser fingerprinting bypass.

## 🛠️ Tech Stack
- **Backend**: FastAPI (Python 3.9+)
- **Frontend**: Bootstrap 5, Vanilla JS (Professional Greyscale Theme)
- **Engine**: Asyncio, Playwright, Nmap
- **Database**: SQLite with WAL mode

## 🚦 Quick Start
1. **Clone & Install**:
   ```bash
   git clone https://github.com/AbazarAdam/ReconMaster.git
   cd ReconMaster
   pip install -r requirements.txt
   playwright install chromium
   ```
2. **Launch Dashboard**:
   ```bash
   python main.py --web
   ```
3. **Start Scanning**: Navigate to `http://localhost:8000`, enter your target, and watch the results roll in.

## 📂 Project Structure
- `core/`: Orchestration engine and shared utilities.
- `modules/`: Specialized reconnaissance plugins.
- `web/`: FastAPI application and static assets.
- `reports/`: Generated screenshots and logs.

## ⚖️ License
MIT License - See `LICENSE` for details.
