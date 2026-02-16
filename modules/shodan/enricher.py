import asyncio
import logging
import socket
from typing import Any, Dict, List, Set

import shodan

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class ShodanEnricher(BaseModule):
    """Enriches discoveries with metadata from the Shodan search engine.

    Collects IP addresses discovered in previous phases (e.g., portscan) and
    queries Shodan for organizational data, operating systems, and banners.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "enricher"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "shodan"

    async def run(self, target: str) -> None:
        """Main execution logic for the Shodan module.

        Args:
            target: The domain to enrich data for.
        """
        try:
            api_key = self.config.get("api_keys", {}).get("shodan")
            if not api_key:
                logger.warning("[SHODAN] API key missing. Skipping enrichment.")
                return

            # 1. Retrieve IPs already discovered for this target from the database
            results = self.db.get_results(target, module="portscan/scanner")
            ips: Set[str] = set()
            for res in results:
                data = res.get("data")
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("ip"):
                        ips.add(entry["ip"])

            if not ips:
                # If no IPs found in DB, attempt a direct resolution of the target domain
                try:
                    logger.debug(f"[SHODAN] Resolving {target} for enrichment...")
                    ip = await asyncio.to_thread(socket.gethostbyname, target)
                    ips.add(ip)
                except Exception as e:
                    logger.error(f"[SHODAN] Failed to resolve target {target}: {e}")
                    return

            logger.info(f"[SHODAN] Enriching {len(ips)} IP(s) via Shodan for {target}...")

            # 2. Query Shodan for each identified IP
            api = shodan.Shodan(api_key)
            findings = []

            for ip in ips:
                if self.limiter:
                    await self.limiter.acquire()

                try:
                    # Shodan library is blocking; offload to a thread
                    host_info = await asyncio.to_thread(api.host, ip)

                    enrichment = {
                        "ip": ip,
                        "org": host_info.get("org", "Unknown"),
                        "os": host_info.get("os", "Unknown"),
                        "ports": host_info.get("ports", []),
                        "vulns": host_info.get("vulns", []),
                        "hostnames": host_info.get("hostnames", []),
                        "data": [],
                    }

                    for item in host_info.get("data", []):
                        enrichment["data"].append(
                            {
                                "port": item.get("port"),
                                "banner": item.get("data", "").strip()[:500],
                                "service": item.get("product", "Unknown"),
                            }
                        )

                    findings.append(enrichment)
                    logger.debug(f"[SHODAN] Successfully enriched {ip}")

                except shodan.APIError as e:
                    logger.error(f"[SHODAN] API error for {ip}: {e}")
                except Exception as e:
                    logger.error(f"[SHODAN] Unexpected enrichment error for {ip}: {e}")

            if findings:
                self.store_results(target, "shodan", "enrichment", findings)
                logger.info(f"[SHODAN] Successfully stored enrichment for {len(findings)} IPs")
            else:
                logger.info(f"[SHODAN] No Shodan data discovered for {target}")

        except Exception as e:
            logger.error(f"[SHODAN] Module execution failed: {e}")
