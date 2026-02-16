import asyncio
import logging
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock

# Add project root to path
sys.path.append(os.getcwd())

from modules.screenshot.capturer import ScreenshotCapturer
from core.database import Database

# Setup logging to console
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger("test_screenshot")

async def run_standalone_test():
    logger.info("Starting standalone screenshot test...")
    
    # 1. Setup mock/real components
    db = Database("test_recon.db")
    # Add a dummy result for the detector to find
    target = "scanme.nmap.org"
    scan_id = "test_standalone_screenshot"
    
    logger.info(f"Injecting test data for {target} into DB...")
    db.store_result(
        target=target,
        module="http/detector",
        source="http",
        result_type="http",
        data=[{"url": "http://scanme.nmap.org"}, {"url": "https://scanme.nmap.org"}],
        scan_id=scan_id
    )
    
    config = {
        "timeout": 15,
        "concurrency": 2
    }
    
    # 2. Instantiate Capturer
    # Mocking BaseModule necessities
    # BaseModule signature: (config, database, scan_id, rate_limiter, proxy_manager)
    capturer = ScreenshotCapturer(config, db)
    capturer.scan_id = scan_id
    
    logger.info("Running ScreenshotCapturer.run()...")
    
    # 3. Run with timeout to detect hangs
    try:
        await asyncio.wait_for(capturer.run(target), timeout=90)
        logger.info("ScreenshotCapturer.run() completed successfully.")
    except asyncio.TimeoutError:
        logger.error("ScreenshotCapturer.run() HANGED (90s timeout reached)!")
    except Exception as e:
        import traceback
        logger.error(f"ScreenshotCapturer.run() failed with error: {e}")
        logger.error(traceback.format_exc())
    
    # 4. Verify results
    logger.info("Checking results in database...")
    results = db.get_results(target, module="screenshot/capturer", scan_id=scan_id)
    if results:
        logger.info(f"Found {len(results)} screenshot results in DB.")
        for res in results:
            logger.info(f"Result: {res.get('data')}")
    else:
        logger.warning("No screenshot results found in DB.")
        
    # Check if files exist
    screenshot_dir = Path("reports/screenshots")
    if screenshot_dir.exists():
        files = list(screenshot_dir.glob("*.png"))
        logger.info(f"Found {len(files)} screenshot files in {screenshot_dir}")
    else:
        logger.warning(f"Screenshot directory {screenshot_dir} does not exist.")

if __name__ == "__main__":
    asyncio.run(run_standalone_test())
