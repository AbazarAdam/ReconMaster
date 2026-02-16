import asyncio
import logging
from typing import Any, Dict, List, Set

import aiohttp
from bs4 import BeautifulSoup

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class HttpDetector(BaseModule):
    """Detects and probes HTTP/HTTPS services on discovered subdomains.

    Identifies active web servers, retrieves page titles, and extracts server headers.
    Prioritizes subdomains that were found to have common web ports open.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "detector"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "http"

    async def run(self, target: str) -> None:
        """Main execution logic for the HTTP Detector module.

        Args:
            target: The domain to probe for HTTP services.
        """
        try:
            # 1. Collect subdomains from the database (discovery results)
            discovery_results = self.db.get_results(target, module="subdomain")
            subdomains: Set[str] = set()
            for res in discovery_results:
                data = res.get("data", [])
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict) and "subdomain" in item:
                        subdomains.add(item["subdomain"])

            # 2. Collect targets from portscan results that had HTTP-ready ports
            port_results = self.db.get_results(target, module="portscan")
            prioritized: Set[str] = set()
            for res in port_results:
                items = res.get("data", [])
                if not isinstance(items, list):
                    items = [items]
                for item in items:
                    if item.get("port") in [80, 443, 8000, 8080, 8443, 8888]:
                        # If we have a 'host' or 'target' from the portscan, use it
                        prioritized.add(item.get("host") or target)

            # 3. Combine and limit targets to ensure stability
            all_targets = list(prioritized) + [
                s for s in subdomains if s not in prioritized
            ]
            if not all_targets:
                all_targets = [target]

            limit = self.config.get("probing_limit", 100)
            if len(all_targets) > limit:
                logger.info(
                    f"[HTTP] Limiting probes to {limit} out of {len(all_targets)} targets"
                )
                all_targets = all_targets[:limit]

            # 4. Probing configuration
            timeout = aiohttp.ClientTimeout(total=5, connect=3)
            concurrency = self.config.get("concurrency", 20)
            semaphore = asyncio.Semaphore(concurrency)

            async def probe(host: str, session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
                """Probes both HTTP and HTTPS for a given host."""
                async with semaphore:
                    results = []
                    for proto in ["http", "https"]:
                        url = f"{proto}://{host}"
                        if self.limiter:
                            await self.limiter.acquire()
                        try:
                            async with session.get(
                                url,
                                timeout=timeout,
                                allow_redirects=True,
                                ssl=False,
                                proxy=self.get_request_proxy(),
                            ) as response:
                                # Read limited content for title extraction
                                body = await response.content.read(128 * 1024)
                                html = body.decode("utf-8", errors="ignore")
                                soup = BeautifulSoup(html, "lxml")
                                title = (
                                    soup.title.string.strip()
                                    if soup.title and soup.title.string
                                    else "No Title"
                                )

                                results.append(
                                    {
                                        "url": str(response.url),
                                        "status": response.status,
                                        "server": response.headers.get("Server", "N/A"),
                                        "title": title,
                                        "x-powered-by": response.headers.get(
                                            "X-Powered-By", "N/A"
                                        ),
                                    }
                                )
                        except Exception:
                            continue  # Silently skip connection failures
                    return results

            # 5. Execute probes
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                tasks = [probe(sub, session) for sub in all_targets]
                
                raw_findings = []
                total = len(tasks)
                completed = 0
                
                logger.info(f"[HTTP] Starting discovery for {total} potential services...")
                
                for coro in asyncio.as_completed(tasks):
                    res_list = await coro
                    raw_findings.extend(res_list)
                    completed += 1
                    if completed % 10 == 0 or completed == total:
                        logger.debug(f"[HTTP] Probing progress: {completed}/{total}")

            # 6. Store aggregate results
            if raw_findings:
                self.store_results(target, "http_detector", "http", raw_findings)
                logger.info(f"[HTTP] Successfully identified {len(raw_findings)} services")
            else:
                logger.info(f"[HTTP] No active HTTP services discovered for {target}")

        except Exception as e:
            logger.error(f"[HTTP] Module execution failed: {e}")

