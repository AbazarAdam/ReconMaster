import logging
from typing import Any, List, Optional, Set

import aiohttp

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class CertificateTransparency(BaseModule):
    """Fetches subdomains for a target domain using Certificate Transparency logs from crt.sh.

    CT logs are a highly effective way to find subdomains that have had SSL/TLS certificates issued.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "ct"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "subdomain"

    async def run(self, target: str) -> None:
        """Main execution logic for the CT.sh module.

        Args:
            target: The domain to discover subdomains for.
        """
        if not self.validate_target(target):
            logger.error(f"[CT] Invalid target format: {target}")
            return

        url = f"https://crt.sh/?q=%.{target}&output=json"
        logger.info(f"[CT] Searching Certificate Transparency logs on crt.sh for {target}...")

        try:
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()

                async with session.get(
                    url, timeout=60, proxy=self.get_request_proxy()
                ) as response:
                    if response.status != 200:
                        logger.warning(
                            f"[CT] crt.sh returned non-200 status: {response.status}"
                        )
                        return

                    try:
                        data = await response.json()
                    except aiohttp.ContentTypeError:
                        # Sometimes crt.sh returns an error page (HTML) even with JSON output requested
                        logger.error("[CT] Received invalid JSON response from crt.sh (likely a server-side error)")
                        return

                    subdomains: Set[str] = set()
                    for entry in data:
                        name_value = entry.get("name_value", "")
                        # name_value can contain multiple domains separated by newline
                        for domain in name_value.split("\n"):
                            domain = domain.strip().lower()
                            # Strip wildcards if present
                            if domain.startswith("*."):
                                domain = domain[2:]

                            if domain.endswith(target) and domain != target:
                                subdomains.add(domain)

                    findings = [
                        {"subdomain": sub, "source": "crt.sh"}
                        for sub in sorted(list(subdomains))
                    ]

                    if findings:
                        self.store_results(target, "crt.sh", "subdomain", findings)
                        logger.info(
                            f"[CT] Successfully discovered {len(findings)} subdomains"
                        )
                    else:
                        logger.info(f"[CT] No certificates found for {target}")

        except asyncio.TimeoutError:
            logger.error(f"[CT] Connection timed out while querying crt.sh for {target}")
        except Exception as e:
            logger.error(f"[CT] Unexpected error querying crt.sh: {e}")
