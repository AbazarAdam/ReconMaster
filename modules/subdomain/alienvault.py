import aiohttp
import logging
from typing import Set
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class AlienVault(BaseModule):
    @property
    def name(self) -> str:
        return "alienvault"

    @property
    def module_type(self) -> str:
        return "subdomain"

    async def run(self, target: str):
        """
        Fetches subdomains from AlienVault OTX.
        URL: https://otx.alienvault.com/api/v1/indicators/domain/{target}/passive_dns
        """
        if not self.validate_target(target):
            logger.error(f"Invalid target: {target}")
            return

        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{target}/passive_dns"
        logger.info(f"Searching AlienVault OTX for {target}...")

        try:
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()
                async with session.get(url, timeout=30, proxy=self.get_request_proxy()) as response:
                    if response.status != 200:
                        logger.error(f"AlienVault returned status {response.status}")
                        return

                    data = await response.json()
                    subdomains: Set[str] = set()
                    
                    for record in data.get("passive_dns", []):
                        hostname = record.get("hostname", "").lower()
                        if hostname.endswith(target) and hostname != target:
                            subdomains.add(hostname)

                    findings = [{"subdomain": sub, "source": "alienvault"} for sub in sorted(list(subdomains))]
                    
                    if findings:
                        self.store_results(target, "alienvault", findings)
                        logger.info(f"Found {len(findings)} subdomains for {target} via AlienVault")
                    else:
                        logger.info(f"No subdomains found for {target} via AlienVault")

        except Exception as e:
            logger.error(f"Error querying AlienVault: {e}")

