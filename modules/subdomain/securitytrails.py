import aiohttp
import logging
from typing import Set
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class SecurityTrails(BaseModule):
    """Fetches subdomains for a target domain using the SecurityTrails API.

    Requires an API key to be configured in 'api_keys.securitytrails'.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "securitytrails"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "subdomain"

    async def run(self, target: str) -> None:
        """Main execution logic for the SecurityTrails module.

        Args:
            target: The domain to discover subdomains for.
        """
        api_key = self.config.get("api_keys", {}).get("securitytrails")
        if not api_key:
            logger.warning("[SECURITYTRAILS] API key missing. Skipping discovery.")
            return

        if not self.validate_target(target):
            logger.error(f"[SECURITYTRAILS] Invalid target format: {target}")
            return

        url = f"https://api.securitytrails.com/v1/domain/{target}/subdomains"
        headers = {"APIKEY": api_key}
        logger.info(f"[SECURITYTRAILS] Searching SecurityTrails database for {target}...")

        try:
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()

                async with session.get(
                    url, headers=headers, timeout=30, proxy=self.get_request_proxy()
                ) as response:
                    if response.status == 403:
                        logger.error(
                            "[SECURITYTRAILS] API key invalid or rate limit exceeded"
                        )
                        return
                    if response.status != 200:
                        logger.warning(
                            f"[SECURITYTRAILS] API returned status {response.status}"
                        )
                        return

                    data = await response.json()
                    subdomains: Set[str] = set()

                    for sub in data.get("subdomains", []):
                        full_domain = f"{sub}.{target}".lower()
                        subdomains.add(full_domain)

                    findings = [
                        {"subdomain": sub, "source": "securitytrails"}
                        for sub in sorted(list(subdomains))
                    ]

                    if findings:
                        self.store_results(target, "securitytrails", findings)
                        logger.info(
                            f"[SECURITYTRAILS] Successfully discovered {len(findings)} subdomains"
                        )
                    else:
                        logger.info(f"[SECURITYTRAILS] No records found for {target}")

        except Exception as e:
            logger.error(f"[SECURITYTRAILS] Failed to query SecurityTrails API: {e}")
