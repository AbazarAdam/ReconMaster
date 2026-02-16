import aiohttp
import logging
from typing import Set, Dict, Any
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class VirusTotal(BaseModule):
    @property
    def name(self) -> str:
        return "virustotal"

    @property
    def module_type(self) -> str:
        return "subdomain"

    async def run(self, target: str):
        """
        Fetches subdomains from VirusTotal.
        Requires API Key in config: api_keys.virustotal
        URL: https://www.virustotal.com/api/v3/domains/{target}/subdomains
        """
        logger.debug(f"[MODULE DEBUG] Entering VirusTotal.run for target: {target}")
        try:
            api_key = self.config.get("api_keys", {}).get("virustotal")
            if not api_key:
                logger.warning("VirusTotal API key missing. Skipping module.")
                return

            if not self.validate_target(target):
                logger.error(f"Invalid target: {target}")
                return

            url = f"https://www.virustotal.com/api/v3/domains/{target}/subdomains?limit=40"
            headers = {"x-apikey": api_key}
            logger.info(f"Searching VirusTotal for {target}...")

            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()
                async with session.get(url, headers=headers, timeout=30, proxy=self.get_request_proxy()) as response:
                    if response.status == 401:
                        logger.error("VirusTotal API key is invalid.")
                        return
                    if response.status != 200:
                        logger.error(f"VirusTotal returned status {response.status}")
                        return

                    data = await response.json()
                    subdomains: Set[str] = set()
                    
                    for item in data.get("data", []):
                        sub = item.get("id", "").lower()
                        if sub.endswith(target) and sub != target:
                            subdomains.add(sub)

                    findings = [{"subdomain": sub, "source": "virustotal"} for sub in sorted(list(subdomains))]
                    
                    if findings:
                        self.store_results(target, "virustotal", findings)
                        logger.info(f"Found {len(findings)} subdomains for {target} via VirusTotal")
                    else:
                        logger.info(f"No subdomains found for {target} via VirusTotal")

        except Exception as e:
            import traceback
            logger.error(f"Error querying VirusTotal: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting VirusTotal.run for target: {target}")

