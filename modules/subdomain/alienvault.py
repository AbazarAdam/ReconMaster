import logging
from typing import Set

import aiohttp

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class AlienVault(BaseModule):
    """Fetches subdomains for a target domain from AlienVault OTX (Open Threat Exchange).

    Uses the passive DNS endpoint to discover historical subdomain records.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "alienvault"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "subdomain"

    async def run(self, target: str) -> None:
        """Main execution logic for the AlienVault module.

        Args:
            target: The domain to discover subdomains for.
        """
        if not self.validate_target(target):
            logger.error(f"[ALIENVAULT] Invalid target format: {target}")
            return

        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{target}/passive_dns"
        logger.info(f"[ALIENVAULT] Querying passive DNS records for {target}...")

        try:
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()

                async with session.get(
                    url, timeout=30, proxy=self.get_request_proxy()
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            f"[ALIENVAULT] API returned non-200 status: {response.status}"
                        )
                        return

                    data = await response.json()
                    subdomains: Set[str] = set()

                    for record in data.get("passive_dns", []):
                        hostname = record.get("hostname", "").lower()
                        if hostname.endswith(target) and hostname != target:
                            subdomains.add(hostname)

                    findings = [
                        {"subdomain": sub, "source": "alienvault"}
                        for sub in sorted(list(subdomains))
                    ]

                    if findings:
                        self.store_results(target, "alienvault", findings)
                        logger.info(
                            f"[ALIENVAULT] Successfully discovered {len(findings)} subdomains"
                        )
                    else:
                        logger.info(f"[ALIENVAULT] No records found for {target}")

        except Exception as e:
            logger.error(f"[ALIENVAULT] Failed to query OTX API: {e}")

