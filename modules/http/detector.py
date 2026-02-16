import aiohttp
import asyncio
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class HttpDetector(BaseModule):
    @property
    def name(self) -> str:
        return "detector"

    @property
    def module_type(self) -> str:
        return "http"

    async def run(self, target: str):
        """
        Detects HTTP services on discovered subdomains.
        """
        logger.debug(f"[MODULE DEBUG] Entering HttpDetector.run for target: {target}")
        try:
            # Query database for subdomains of this target
            results = self.db.get_results(target, module="subdomain")
            subdomains = set()
            for res in results:
                if isinstance(res['data'], list):
                    for item in res['data']:
                        if 'subdomain' in item:
                            subdomains.add(item['subdomain'])

            # Prioritize subdomains that had open ports 80, 443, 8080, 8443
            port_results = self.db.get_results(target, module="portscan")
            prioritized = set()
            for res in port_results:
                items = res.get('data', [])
                if not isinstance(items, list): items = [items]
                for item in items:
                    if item.get('port') in [80, 443, 8000, 8080, 8443, 8888]:
                        if item.get('host'): prioritized.add(item['host'])

            # Combine and limit
            all_subs = list(prioritized) + [s for s in list(subdomains) if s not in prioritized]
            limit = self.config.get("probing_limit", 100) # Lower to 100 for stability
            if len(all_subs) > limit:
                logger.info(f"Limiting HTTP probing to {limit} out of {len(all_subs)} targets.")
                all_subs = all_subs[:limit]

            if not all_subs:
                all_subs = [target]

            # Aggressive timeouts: 3s connect, 5s total
            timeout = aiohttp.ClientTimeout(total=5, connect=3)
            concurrency = self.config.get("concurrency", 20) # Lower concurrency for stability on windows
            semaphore = asyncio.Semaphore(concurrency)

            async def probe(subdomain, session):
                async with semaphore:
                    results = []
                    for proto in ["http", "https"]:
                        url = f"{proto}://{subdomain}"
                        if self.limiter:
                            await self.limiter.acquire()
                        try:
                            async with session.get(url, timeout=timeout, allow_redirects=True, ssl=False, proxy=self.get_request_proxy()) as response:
                                    # Read small chunk of content
                                    try:
                                        body = await response.content.read(128 * 1024)
                                        html = body.decode('utf-8', errors='ignore')
                                        soup = BeautifulSoup(html, "lxml")
                                        title = soup.title.string.strip() if soup.title and soup.title.string else "No Title"
                                    except Exception:
                                        title = "Read Error"
                                    
                                    info = {
                                        "url": str(response.url),
                                        "status": response.status,
                                        "server": response.headers.get("Server", "Unknown"),
                                        "title": title,
                                        "x-powered-by": response.headers.get("X-Powered-By", "Unknown")
                                    }
                                    results.append(info)
                                    logger.debug(f"[HTTP] Found service: {url} -> {response.status}")
                        except Exception as e:
                            # Silently skip most errors, log only debug
                            continue
                    return results

            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                tasks = [probe(sub, session) for sub in all_subs]
                
                raw_findings = []
                total = len(tasks)
                completed = 0
                
                # Use as_completed to process results as they come
                for coro in asyncio.as_completed(tasks):
                    res_list = await coro
                    raw_findings.extend(res_list)
                    completed += 1
                    if completed % 5 == 0 or completed == total:
                        logger.info(f"HTTP probing progress: {completed}/{total} subdomains checked...")
            
            if raw_findings:
                self.store_results(target, "http_detector", "http", raw_findings)
                logger.info(f"Successfully detected {len(raw_findings)} HTTP services for {target}")
            else:
                logger.info(f"No HTTP services detected for {target}")
        except Exception as e:
            import traceback
            logger.error(f"HTTP detection failed for {target}: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting HttpDetector.run for target: {target}")

