import logging
from typing import Any, Dict, Set

import aiohttp

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class VirusTotal(BaseModule):
    """Fetches subdomains for a target domain using the VirusTotal v3 API.

    Requires an API key to be configured in 'api_keys.virustotal'.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "virustotal"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "subdomain"

    async def run(self, target: str) -> None:
        """Main execution logic for the VirusTotal module.

        Args:
            target: The domain to discover subdomains for.
        """
        api_key = self.config.get("api_keys", {}).get("virustotal")
        if not api_key:
            logger.warning("[VIRUSTOTAL] API key missing. Skipping discovery.")
            return

        if not self.validate_target(target):
            logger.error(f"[VIRUSTOTAL] Invalid target format: {target}")
            return

        url = f"https://www.virustotal.com/api/v3/domains/{target}/subdomains?limit=40"
        headers = {"x-apikey": api_key}
        logger.info(f"[VIRUSTOTAL] Searching VirusTotal database for {target}...")

        try:
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()

                async with session.get(
                    url, headers=headers, timeout=30, proxy=self.get_request_proxy()
                ) as response:
                    if response.status == 401:
                        logger.error("[VIRUSTOTAL] API key is invalid")
                        return
                    if response.status != 200:
                        logger.warning(
                            f"[VIRUSTOTAL] API returned status {response.status}"
                        )
                        return

                    data = await response.json()
                    subdomains: Set[str] = set()

                    for item in data.get("data", []):
                        sub = item.get("id", "").lower()
                        if sub.endswith(target) and sub != target:
                            subdomains.add(sub)

                    findings = [
                        {"subdomain": sub, "source": "virustotal"}
                        for sub in sorted(list(subdomains))
                    ]

                    if findings:
                        self.store_results(target, "virustotal", findings)
                        logger.info(
                            f"[VIRUSTOTAL] Successfully discovered {len(findings)} subdomains"
                        )
                    else:
                        logger.info(f"[VIRUSTOTAL] No records found for {target}")

        except Exception as e:
            logger.error(f"[VIRUSTOTAL] Failed to query VirusTotal API: {e}")
