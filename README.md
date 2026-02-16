# ReconMaster

**ReconMaster** is a modular, high-performance reconnaissance framework designed for modern security researchers and OSINT enthusiasts. It provides a centralized hub for automating technical discovery, service enumeration, and data enrichment using a phase-based execution engine.

![ReconMaster Dashboard](https://raw.githubusercontent.com/abaze/ReconMaster/main/assets/banner.png)

## 🎯 Key Features

*   **⚡ Async Orchestration**: Leverages Python's `asyncio` for high-concurrency, parallel module execution.
*   **🧩 Modular Architecture**: Easily extensible system with standardized `BaseModule` interfaces.
*   **🕵️ Multi-Source Discovery**: Integrates with crt.sh, AlienVault, VirusTotal, SecurityTrails, and more.
*   **🌐 Service Intelligence**: Automatic HTTP detection, header analysis, and title extraction.
*   **📸 Visual Recon**: Headless Playwright-based screenshot capture for discovered web services.
*   **💎 Data Enrichment**: Built-in Shodan and GitHub connectors for advanced metadata gathering.
*   **📊 Web Dashboard**: Sleek, professional greyscale interface for scan management and reporting.
*   **🛡️ Stealth & Control**: Global rate limiting and full SOCKS/Tor proxy support.

## 🚀 Quick Start

### 1. Prerequisites
- Python 3.10 or higher
- [Playwright](https://playwright.dev/python/docs/intro) (for screenshots)

### 2. Installation
```bash
# Clone the repository
git clone https://github.com/abaze/ReconMaster.git
cd ReconMaster

# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers (required for screenshot module)
playwright install chromium
```

### 3. Usage

#### Start the Web Dashboard
```bash
uvicorn web.app:app --host 0.0.0.0 --port 8000
```
Navigate to `http://localhost:8000` to initialize your first scan.

#### Run via CLI
```bash
python main.py example.com
```

## ⚙️ Configuration

All system settings are managed via `config/default.yaml`.

```yaml
api_keys:
  virustotal: "YOUR_KEY"
  shodan: "YOUR_KEY"
  github: "YOUR_KEY"

rate_limit: 10
proxy:
  use_tor: false
```

## 🏗️ Project Structure

- `core/`: High-level orchestration, state management, and infrastructure.
- `modules/`: Standardized reconnaissance and discovery logic.
- `web/`: FastAPI-powered dashboard and REST API.
- `config/`: Centralized YAML configurations.
- `reports/`: Local storage for screenshots and session logs.

## 📖 Documentation

For detailed technical guides, please refer to:
- [Module Creation Guide](docs/MODULE_CREATION.md)
- [API Reference](docs/API_REFERENCE.md)
- [Project Report](PROJECT_REPORT.md)

## 🤝 Contributing

Contributions are welcome! Please feel free to submit pull requests or open issues for feature requests and bug reports.

## 📜 License

Distributed under the **MIT License**. See `LICENSE` for more information.
