import asyncio
import logging
import sys
import uuid
from typing import Any, Callable, Dict, List, Optional

from core.config import load_config, setup_logging
from core.database import Database
from core.module_loader import ModuleLoader

# Ensure ProactorEventLoop is used on Windows for subprocess support (needed for Playwright)
if sys.platform == "win32":
    try:
        if not isinstance(
            asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy
        ):
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    except Exception:
        pass

logger = logging.getLogger(__name__)


async def run_scan(
    target: str,
    config_path: Optional[str] = None,
    scan_id: Optional[str] = None,
    progress_callback: Optional[Callable[[Dict[str, Any]], Any]] = None,
) -> None:
    """Orchestrates the full multi-phase reconnaissance scan against a target.

    This function is the main entry point for the scan engine. It handles configuration
    loading, infrastructure initialization, phase sequencing, and results summarization.

    Args:
        target: The domain or IP address to scan.
        config_path: Optional path to a custom YAML configuration file.
        scan_id: Optional unique identifier for the scan. If not provided, one will be generated.
        progress_callback: Optional async function called with status updates (JSON).
    """
    # 1. Configuration & Logging Setup
    config = load_config(config_path or "config/default.yaml")
    log_settings = config.get("logging", {})
    setup_logging(
        level=log_settings.get("level", "INFO"),
        log_file=log_settings.get("file", "recon.log"),
    )

    logger.info(f"[ENGINE] Starting comprehensive scan for target: {target}")
    if progress_callback:
        await progress_callback(
            {
                "type": "status",
                "status": "running",
                "message": f"Initializing scan for {target}",
            }
        )

    # 2. Database Initialization
    db_path = config.get("database", "recon.db")
    db = Database(db_path)

    if not scan_id:
        scan_id = f"cli_{str(uuid.uuid4())[:8]}"
        logger.info(f"[ENGINE] Auto-generated scan ID: {scan_id}")

    db.create_scan(scan_id, target, "running")

    # 3. Infrastructure Setup (Rate Limiters, Proxies, etc.)
    from core.proxy_manager import ProxyManager
    from core.rate_limiter import RateLimiter

    rate_limit = config.get("rate_limit", 10)
    limiter = RateLimiter(rate_limit)
    proxy_manager = ProxyManager(config.get("proxy", {}))
    modules_config = config.get("modules", {})
    loader = ModuleLoader()

    # 4. Phase Execution Logic
    async def execute_phase(label: str, module_types: List[str]) -> None:
        """Executes a logical group of modules in parallel.

        Args:
            label: Human-readable name for the phase (e.g., "Phase 1: Discovery").
            module_types: List of module categories to execute in this phase.
        """
        tasks = []
        if progress_callback:
            await progress_callback(
                {"type": "phase", "phase": label, "modules": module_types}
            )

        for m_type in module_types:
            # Prepare configuration subset for this module type
            phase_modules = {
                **modules_config,
                "enabled": {
                    m_type: modules_config.get("enabled", {}).get(m_type, [])
                },
            }
            m_cfg = {
                "modules": phase_modules,
                "api_keys": config.get("api_keys", {}),
                "rate_limit": rate_limit,
                "proxy": config.get("proxy", {}),
            }

            loaded = await loader.load_enabled_modules(
                m_cfg,
                db,
                scan_id=scan_id,
                rate_limiter=limiter,
                proxy_manager=proxy_manager,
            )

            async def run_module_safe(m: Any, inner_target: str) -> None:
                """Runs a module with localized error handling and reporting."""
                try:
                    logger.debug(f"[ENGINE] Launching {m.module_type}/{m.name}")
                    await m.run(inner_target)
                    logger.debug(f"[ENGINE] Module {m.name} completed successfully")
                    if progress_callback:
                        await progress_callback(
                            {"type": "module_end", "module": m.name, "status": "completed"}
                        )
                except Exception as e:
                    import traceback
                    logger.error(f"[ENGINE ERROR] Module {m.name} encountered a fault: {e}")
                    logger.debug(f"Full traceback: {traceback.format_exc()}")
                    if progress_callback:
                        await progress_callback(
                            {
                                "type": "module_end",
                                "module": m.name,
                                "status": "failed",
                                "error": str(e),
                            }
                        )
                        await progress_callback(
                            {"type": "error", "message": f"{m.name} failed: {str(e)}"}
                        )

            tasks.extend([run_module_safe(m, target) for m in loaded])

        # Windows-specific Playwright loop fix (threaded fallback)
        if label == "Phase 5: Visual Recon" and sys.platform == "win32":
            try:
                loop = asyncio.get_event_loop()
                if not isinstance(
                    loop, asyncio.WindowsProactorEventLoopPolicy()._loop_factory
                ):
                    logger.warning(
                        "[ENGINE] Detected Selector loop on Windows. Offloading Phase 5 to Proactor thread..."
                    )

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
                    while t.is_alive():
                        await asyncio.sleep(1)
                    return
            except Exception as e:
                logger.error(f"[ENGINE ERROR] Phase 5 threaded fallback failed: {e}")

        if tasks:
            logger.info(f"[ENGINE] Running {label} with {len(tasks)} parallel tasks...")
            if progress_callback:
                await progress_callback(
                    {"type": "log", "message": f"{label}: Running {len(tasks)} modules..."}
                )

            # Parallel execution with a global safety timeout (5 minutes per phase)
            await asyncio.wait_for(asyncio.gather(*tasks), timeout=300)

    # 5. Pipeline Execution
    try:
        # Sequentially initiate phases
        await execute_phase("Phase 1: Subdomains & Cloud", ["subdomain", "github", "cloud_buckets"])
        await execute_phase("Phase 2: Port Scanning", ["portscan"])
        await execute_phase("Phase 3: Service Enrichment", ["shodan"])
        await execute_phase("Phase 4: HTTP Analysis", ["http"])
        await execute_phase("Phase 5: Visual Recon", ["screenshot"])

        # 6. Post-Scan Cleanup & Summarization
        deduped = db.deduplicate_results(target)
        if deduped:
            logger.info(f"[ENGINE] Purged {deduped} duplicate entries from database")

        results = db.get_results(target, scan_id=scan_id)
        logger.info(f"[ENGINE] Scan completed successfully for {target}")

        # Tabulate findings for logs
        counts = {}
        subdomains = set()
        for res in results:
            r_type = res.get("type", "unknown")
            counts[r_type] = counts.get(r_type, 0) + 1
            if r_type == "subdomain":
                data = res.get("data", [])
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and item.get("subdomain"):
                        subdomains.add(item.get("subdomain"))

        logger.info(f"[ENGINE] Summary for Scan ID {scan_id}:")
        for r_type, count in counts.items():
            logger.info(f"  > {r_type.capitalize()}: {count}")
        if subdomains:
            logger.info(f"  > Unique Subdomains: {len(subdomains)}")

        if scan_id:
            db.update_scan_status(scan_id, "completed")
            if progress_callback:
                await progress_callback(
                    {"type": "status", "status": "completed", "summary": counts}
                )

    except Exception as e:
        import traceback

        logger.error(f"[ENGINE CRITICAL] Scan failed: {e}")
        logger.debug(traceback.format_exc())
        if scan_id:
            db.update_scan_status(scan_id, "failed")
        if progress_callback:
            await progress_callback(
                {"type": "error", "message": f"Global engine failure: {str(e)}"}
            )
        raise e
