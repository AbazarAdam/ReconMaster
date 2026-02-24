import asyncio
import argparse
import sys
import logging
from core.engine import run_scan

def main():
    parser = argparse.ArgumentParser(description="Recon Master - OSINT Automation Tool")
    parser.add_argument("target", nargs="?", help="Domain to scan (e.g., example.com)")
    parser.add_argument("--config", default="config/default.yaml", help="Path to config file")
    parser.add_argument("--web", action="store_true", help="Launch the web dashboard")
    
    args = parser.parse_args()

    if args.web:
        import uvicorn
        print("[*] Launching ReconMaster Web Dashboard...")
        uvicorn.run("web.app:app", host="0.0.0.0", port=8000, reload=True)
        return

    if not args.target:
        parser.print_help()
        sys.exit(1)

    try:
        asyncio.run(run_scan(args.target, args.config))
    except KeyboardInterrupt:
        print("\n[!] Scan interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
