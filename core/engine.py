import asyncio
import logging
import sys
from typing import Optional

# Ensure ProactorEventLoop is used on Windows for subprocess support (needed for Playwright)
if sys.platform == 'win32':
    try:
        if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

from core.config import load_config, setup_logging
from core.database import Database
from core.module_loader import ModuleLoader

logger = logging.getLogger(__name__)

async def run_scan(target: str, config_path: Optional[str] = None, scan_id: Optional[str] = None, progress_callback: Optional[callable] = None):
    """
    Main orchestration logic for running a scan against a target.
    """
    # 1. Load Configuration
    config = load_config(config_path or "config/default.yaml")
    
    # 2. Setup Logging
    log_settings = config.get("logging", {})
    setup_logging(
        level=log_settings.get("level", "INFO"),
        log_file=log_settings.get("file", "recon.log")
    )
    
    logger.info(f"--- Starting Recon Scan for {target} ---")
    if progress_callback:
        await progress_callback({"type": "status", "status": "running", "message": f"Starting scan for {target}"})

    # 3. Initialize Database
    db_path = config.get("database", "recon.db")
    db = Database(db_path)
    
    # Ensure scan_id exists
    import uuid
    if not scan_id:
        scan_id = f"cli_{str(uuid.uuid4())[:8]}"
        logger.info(f"No scan_id provided, generated: {scan_id}")
    
    db.create_scan(scan_id, target, "running")

    # 4. Initialize Infrastructure
    from core.rate_limiter import RateLimiter
    from core.proxy_manager import ProxyManager
    
    rate_limit = config.get("rate_limit", 10)
    limiter = RateLimiter(rate_limit)
    proxy_manager = ProxyManager(config.get("proxy", {}))
    modules_config = config.get("modules", {})
    
    loader = ModuleLoader()

    # 5. Define Scan Phases for Parallel Execution
    async def run_phase(label: str, module_types: list):
        tasks = []
        if progress_callback:
            await progress_callback({"type": "phase", "phase": label, "modules": module_types})
            
        for m_type in module_types:
            phase_modules = {**modules_config, "enabled": {m_type: modules_config.get("enabled", {}).get(m_type, [])}}
            m_cfg = {
                "modules": phase_modules,
                "api_keys": config.get("api_keys", {}),
                "rate_limit": rate_limit,
                "proxy": config.get("proxy", {})
            }
            loaded = await loader.load_enabled_modules(m_cfg, db, scan_id=scan_id, rate_limiter=limiter, proxy_manager=proxy_manager)
            
            # Wrap each module run in a try-except to log entry/exit and handle errors
            async def run_module_safe(m, target):
                try:
                    logger.debug(f"[ENGINE DEBUG] Starting module: {m.module_type}/{m.name}")
                    await m.run(target)
                    logger.debug(f"[ENGINE DEBUG] Completed module: {m.module_type}/{m.name}")
                    if progress_callback:
                        await progress_callback({"type": "module_end", "module": m.name, "status": "completed"})
                except Exception as e:
                    import traceback
                    logger.error(f"[ENGINE ERROR] Module {m.module_type}/{m.name} failed: {e}")
                    logger.error(traceback.format_exc())
                    if progress_callback:
                        await progress_callback({"type": "module_end", "module": m.name, "status": "failed", "error": str(e)})
                        await progress_callback({"type": "error", "message": f"{m.name}: {str(e)}"})
            
            tasks.extend([run_module_safe(m, target) for m in loaded])

        if label == "Phase 5" and sys.platform == 'win32':
            # Special handling for Windows + Playwright + Uvicorn loop issues
            try:
                loop = asyncio.get_event_loop()
                if not isinstance(loop, asyncio.WindowsProactorEventLoopPolicy()._loop_factory):
                    logger.warning("[ENGINE] Detected non-proactor loop on Windows. Running Phase 5 in a separate thread...")
                    
                    def run_phase_threaded():
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            new_loop.run_until_complete(asyncio.gather(*tasks))
                        finally:
                            new_loop.close()
                    
                    import threading
                    t = threading.Thread(target=run_phase_threaded)
                    t.start()
                    # Wait for thread to finish since we are in an async function and phases are sequential
                    while t.is_alive():
                        await asyncio.sleep(1)
                    return
            except Exception as e:
                logger.error(f"[ENGINE ERROR] Failed to run Phase 5 fallback: {e}")

        if tasks:
            logger.info(f"{label}: Running {len(tasks)} modules in parallel...")
            if progress_callback:
                await progress_callback({"type": "log", "message": f"{label}: Running {len(tasks)} modules..."})
            
            # Run all modules in phase
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=300) # Safety timeout

    try:
        # Execute Phases (ordered to satisfy dependencies)
        await run_phase("Phase 1", ["subdomain", "github", "cloud_buckets"])
        await run_phase("Phase 2", ["portscan"])
        await run_phase("Phase 3", ["shodan"])
        await run_phase("Phase 4", ["http"])
        await run_phase("Phase 5", ["screenshot"])

        deduped = db.deduplicate_results(target)
        if deduped:
            logger.info(f"Removed {deduped} duplicate results for {target}")

        # 9. Summary
        # Get all results for this scan_id specifically
        results = db.get_results(target, scan_id=scan_id)
        logger.info(f"--- Scan Completed for {target} ---")
        
        counts = {}
        for res in results:
            r_type = res.get("type", "unknown")
            counts[r_type] = counts.get(r_type, 0) + 1
            
        logger.info(f"Summary of findings for Scan ID {scan_id}:")
        for r_type, count in counts.items():
            logger.info(f"  - {r_type}: {count} entries")

        if counts.get("subdomain"):
            subdomains = set()
            for res in results:
                if res.get("type") == "subdomain":
                    data = res.get('data', [])
                    items = data if isinstance(data, list) else [data]
                    for item in items:
                        if isinstance(item, dict) and item.get("subdomain"):
                            subdomains.add(item.get("subdomain"))
            logger.info(f"Unique subdomains discovered: {len(subdomains)}")
            
        if scan_id:
            db.update_scan_status(scan_id, "completed")
            if progress_callback:
                await progress_callback({"type": "status", "status": "completed", "summary": counts})
                
    except Exception as e:
        import traceback
        logger.error(f"Scan failed: {e}")
        logger.error(traceback.format_exc())
        if scan_id:
            db.update_scan_status(scan_id, "failed")
        if progress_callback:
            await progress_callback({"type": "error", "message": f"Scan failed: {str(e)}"})
        raise e
