import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any
from core.module_loader import BaseModule

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

logger = logging.getLogger(__name__)

class ScreenshotCapturer(BaseModule):
    @property
    def name(self) -> str:
        return "capturer"

    @property
    def module_type(self) -> str:
        return "screenshot"

    async def run(self, target: str):
        """
        Captures screenshots of discovered HTTP services.
        """
        logger.debug(f"[MODULE DEBUG] Entering ScreenshotCapturer.run for target: {target}")
        browser = None
        playwright_mgr = None
        try:
            if async_playwright is None:
                logger.error("Playwright not installed. Skipping screenshots.")
                return

            # Query database for HTTP services
            results = self.db.get_results(target, module="http/detector", scan_id=self.scan_id)
            urls = []
            for res in results:
                data = res.get('data', [])
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and 'url' in item:
                        urls.append(item['url'])

            # Remove duplicates
            urls = list(set(urls))

            if not urls:
                logger.info(f"No HTTP URLs found for screenshot capture (Target: {target}, Scan: {self.scan_id}).")
                return

            output_dir = Path("reports/screenshots")
            output_dir.mkdir(parents=True, exist_ok=True)

            # Configurable timeouts
            browser_timeout = self.config.get("browser_timeout", 60)
            capture_timeout = self.config.get("timeout", 15) * 1000 # Playwright ms
            concurrency = self.config.get("concurrency", 3) # Lower default for stability
            semaphore = asyncio.Semaphore(concurrency)

            async def capture(url, browser_inst):
                async with semaphore:
                    context = None
                    try:
                        if self.limiter:
                            await self.limiter.acquire()
                        
                        logger.debug(f"[SCREENSHOT] Attempting capture: {url}")
                        
                        context = await browser_inst.new_context(
                            viewport={'width': 1280, 'height': 720},
                            ignore_https_errors=True,
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
                        )
                        page = await context.new_page()
                        
                        # Set default timeout for the page context too
                        page.set_default_timeout(capture_timeout)
                        
                        clean_url = url.split("://")[-1].replace("/", "_").replace(":", "_")
                        import re
                        safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', clean_url)
                        if len(safe_name) > 150:
                            safe_name = safe_name[:150]
                            
                        filename = f"{safe_name}.png"
                        filepath = output_dir / filename
                        abs_filepath = filepath.absolute()
                        
                        logger.debug(f"[SCREENSHOT] Navigating to {url}...")
                        try:
                            # Use networkidle with a backup to load
                            await page.goto(url, timeout=capture_timeout, wait_until="networkidle")
                        except Exception as e:
                            logger.debug(f"[SCREENSHOT] Networkidle timed out for {url}, trying 'load': {e}")
                            await page.goto(url, timeout=capture_timeout, wait_until="load")
                        
                        logger.debug(f"[SCREENSHOT] Saving to {abs_filepath}...")
                        await page.screenshot(path=str(filepath))
                        
                        if filepath.exists():
                            logger.info(f"[SCREENSHOT] Successfully captured: {url} -> {filename} ({filepath.stat().st_size} bytes)")
                            # Use forward slashes for URL path consistency
                            relative_path = f"reports/screenshots/{filename}"
                            return {"url": url, "screenshot_path": relative_path}
                        else:
                            logger.error(f"[SCREENSHOT] File was not created: {abs_filepath}")
                            return None
                    except Exception as e:
                        logger.error(f"[SCREENSHOT ERROR] Failed to screenshot {url}: {e}")
                        return None
                    finally:
                        if context:
                            await context.close()

            logger.info(f"Initiating Playwright for {len(urls)} screenshots...")
            
            async with async_playwright() as p:
                playwright_mgr = p
                try:
                    logger.debug("[SCREENSHOT] Launching Chromium browser...")
                    browser = await p.chromium.launch(headless=True)
                    tasks = [capture(url, browser) for url in urls]
                    
                    # Wrap the entire batch in a timeout
                    logger.debug(f"[SCREENSHOT] Awaiting batch completion (timeout: {browser_timeout}s)...")
                    findings = await asyncio.wait_for(asyncio.gather(*tasks), timeout=browser_timeout)
                    
                    valid_findings = [f for f in findings if f is not None]
                    
                    if valid_findings:
                        self.store_results(target, "screenshot_capturer", "screenshot", valid_findings)
                        logger.info(f"Successfully stored {len(valid_findings)} screenshot results for {target}")
                    else:
                        logger.warning(f"Batch completed but no screenshots were successfully saved for {target}")
                
                except asyncio.TimeoutError:
                    logger.error(f"Screenshot batch timed out after {browser_timeout}s")
                finally:
                    if browser:
                        logger.debug("[SCREENSHOT] Closing browser...")
                        await browser.close()

        except Exception as e:
            import traceback
            logger.error(f"Critical error in ScreenshotCapturer: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting ScreenshotCapturer.run for target: {target}")
