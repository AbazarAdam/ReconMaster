import asyncio
import logging
import shodan
from typing import List, Dict, Any
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class ShodanEnricher(BaseModule):
    @property
    def name(self) -> str:
        return "enricher"

    @property
    def module_type(self) -> str:
        return "shodan"

    async def run(self, target: str):
        """
        Enriches target data using Shodan.
        Uses IPs found for the target (e.g. from portscan or subdomain resolution).
        """
        logger.debug(f"[MODULE DEBUG] Entering ShodanEnricher.run for target: {target}")
        try:
            api_key = self.config.get("api_keys", {}).get("shodan")
            if not api_key:
                logger.warning("Shodan API key missing. Skipping module.")
                return

            # 1. Get IPs for this target from the database
            # We can look for 'port' results which usually have an IP
            results = self.db.get_results(target, module="portscan/scanner")
            ips = set()
            for res in results:
                data = res.get("data")
                entries = data if isinstance(data, list) else [data]
                for entry in entries:
                    if isinstance(entry, dict) and entry.get("ip"):
                        ips.add(entry["ip"])
            
            if not ips:
                # Try resolving the target domain itself if no IPs found
                try:
                    import socket
                    ip = await asyncio.to_thread(socket.gethostbyname, target)
                    ips.add(ip)
                except Exception as e:
                    logger.error(f"Failed to resolve {target}: {e}")
                    return

            logger.info(f"Enriching {len(ips)} IPs via Shodan for {target}...")
            
            # 2. Query Shodan for each IP
            api = shodan.Shodan(api_key)
            findings = []

            for ip in ips:
                if self.limiter:
                    await self.limiter.acquire()
                
                try:
                    # Shodan library is blocking, use to_thread
                    host_info = await asyncio.to_thread(api.host, ip)
                    
                    enrichment = {
                        "ip": ip,
                        "org": host_info.get("org", "Unknown"),
                        "os": host_info.get("os", "Unknown"),
                        "ports": host_info.get("ports", []),
                        "vulns": host_info.get("vulns", []),
                        "hostnames": host_info.get("hostnames", []),
                        "data": []
                    }
                    
                    for item in host_info.get("data", []):
                        enrichment["data"].append({
                            "port": item.get("port"),
                            "banner": item.get("data", "").strip()[:500], # limit banner size
                            "service": item.get("product", "Unknown")
                        })
                    
                    findings.append(enrichment)
                    logger.info(f"Retrieved Shodan data for {ip}")

                except shodan.APIError as e:
                    logger.error(f"Shodan API error for {ip}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error querying Shodan for {ip}: {e}")

            if findings:
                self.store_results(target, "shodan", "enrichment", findings)
                logger.info(f"Stored Shodan enrichment for {len(findings)} IPs")
            else:
                logger.info(f"No Shodan data found for {target}")
        except Exception as e:
            import traceback
            logger.error(f"ShodanEnricher failed for {target}: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting ShodanEnricher.run for target: {target}")
