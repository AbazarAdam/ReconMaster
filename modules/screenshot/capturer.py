import asyncio
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.module_loader import BaseModule

try:
    from playwright.async_api import async_playwright
except ImportError:
    async_playwright = None

logger = logging.getLogger(__name__)


class ScreenshotCapturer(BaseModule):
    """Captures visual snapshots of discovered HTTP services using Playwright.

    Orchestrates headless Chromium instances to navigate to identified URLs
    and save PNG screenshots for reporting. Handles concurrency and timeouts
    to ensure system stability.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "capturer"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "screenshot"

    async def run(self, target: str) -> None:
        """Main execution logic for the Screenshot module.

        Args:
            target: The domain to capture screenshots for.
        """
        browser = None
        try:
            if async_playwright is None:
                logger.error("[SCREENSHOT] Playwright not installed. Skipping module.")
                return

            # 1. Retrieve identified HTTP URLs from the database
            results = self.db.get_results(
                target, module="http/detector", scan_id=self.scan_id
            )
            urls = []
            for res in results:
                data = res.get("data", [])
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and "url" in item:
                        urls.append(item["url"])

            urls = list(set(urls))  # Deduplicate
            if not urls:
                logger.info(f"[SCREENSHOT] No active services found to capture for {target}")
                return

            # 2. Prepare output environment
            output_dir = Path("reports/screenshots")
            output_dir.mkdir(parents=True, exist_ok=True)

            # 3. Execution configuration
            browser_timeout = self.config.get("browser_timeout", 300)  # Total module timeout
            capture_timeout = self.config.get("timeout", 45) * 1000  # Per-page timeout (ms)
            concurrency = self.config.get("concurrency", 5)
            semaphore = asyncio.Semaphore(concurrency)

            async def capture(url: str, browser_inst: Any) -> Dict[str, Any]:
                """Navigates to a URL and saves a screenshot."""
                async with semaphore:
                    context = None
                    try:
                        if self.limiter:
                            await self.limiter.acquire()

                        logger.debug(f"[SCREENSHOT] Processing: {url}")
                        
                        context = await browser_inst.new_context(
                            viewport={"width": 1280, "height": 720},
                            ignore_https_errors=True,
                            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
                            java_script_enabled=True,
                        )
                        page = await context.new_page()
                        page.set_default_timeout(capture_timeout)

                        # Generate a safe filename from the URL
                        clean_url = url.split("://")[-1].replace("/", "_").replace(":", "_")
                        safe_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", clean_url)[:150]
                        filename = f"{safe_name}.png"
                        filepath = output_dir / filename

                        # Navigate with refined fallback strategies
                        error_reason = None
                        try:
                            # Try networkidle first (better for SPAs)
                            await page.goto(
                                url, timeout=capture_timeout, wait_until="networkidle"
                            )
                        except Exception as e:
                            logger.debug(f"[SCREENSHOT] networkidle failed for {url}, retrying with load...")
                            try:
                                # Fallback to load state
                                await page.goto(
                                    url, timeout=capture_timeout, wait_until="load"
                                )
                            except Exception as e2:
                                # Final fallback to domcontentloaded
                                try:
                                    logger.debug(f"[SCREENSHOT] load failed for {url}, final attempt with domcontentloaded...")
                                    await page.goto(
                                        url, timeout=capture_timeout, wait_until="domcontentloaded"
                                    )
                                except Exception as e3:
                                    error_reason = str(e3)

                        if not error_reason:
                            # Give a tiny bit of extra time for dynamic elements after load
                            await asyncio.sleep(1)
                            await page.screenshot(path=str(filepath))
                            
                            if filepath.exists():
                                logger.info(f"[SCREENSHOT] Saved: {filename}")
                                return {
                                    "url": url,
                                    "screenshot_path": f"reports/screenshots/{filename}",
                                    "status": "success"
                                }
                            else:
                                error_reason = "File system error: Image not saved"
                                
                        return {
                            "url": url,
                            "screenshot_path": None,
                            "status": "failed",
                            "error": error_reason or "Unknown navigation error"
                        }

                    except Exception as e:
                        logger.warning(f"[SCREENSHOT] Failed to capture {url}: {e}")
                        return {
                            "url": url,
                            "screenshot_path": None,
                            "status": "failed",
                            "error": str(e)
                        }
                    finally:
                        if context:
                            await context.close()

            # 4. Initiate Playwright orchestration
            logger.info(f"[SCREENSHOT] Launching browser for {len(urls)} targets...")
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
                )
                tasks = [capture(url, browser) for url in urls]
                
                try:
                    results_list = await asyncio.wait_for(
                        asyncio.gather(*tasks), timeout=browser_timeout
                    )
                    valid_findings = [f for f in results_list if f is not None]

                    if valid_findings:
                        self.store_results(
                            target, "screenshot_capturer", "screenshot", valid_findings
                        )
                        success_count = len([f for f in valid_findings if f.get("status") == "success"])
                        logger.info(
                            f"[SCREENSHOT] Processed {len(valid_findings)} URLs | Success: {success_count} | Failed: {len(valid_findings) - success_count}"
                        )
                    else:
                        logger.warning("[SCREENSHOT] No screenshot results were generated")

                except asyncio.TimeoutError:
                    logger.error(f"[SCREENSHOT] Batch operation timed out after {browser_timeout}s")

        except Exception as e:
            logger.error(f"[SCREENSHOT] Module failure: {e}")
        finally:
            if browser:
                await browser.close()
