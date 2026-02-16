import aiohttp
import logging
from typing import Set
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class SecurityTrails(BaseModule):
    @property
    def name(self) -> str:
        return "securitytrails"

    @property
    def module_type(self) -> str:
        return "subdomain"

    async def run(self, target: str):
        """
        Fetches subdomains from SecurityTrails.
        Requires API Key in config: api_keys.securitytrails
        URL: https://api.securitytrails.com/v1/domain/{target}/subdomains
        """
        logger.debug(f"[MODULE DEBUG] Entering SecurityTrails.run for target: {target}")
        try:
            api_key = self.config.get("api_keys", {}).get("securitytrails")
            if not api_key:
                logger.warning("SecurityTrails API key missing. Skipping module.")
                return

            if not self.validate_target(target):
                logger.error(f"Invalid target: {target}")
                return

            url = f"https://api.securitytrails.com/v1/domain/{target}/subdomains"
            headers = {"APIKEY": api_key}
            logger.info(f"Searching SecurityTrails for {target}...")

            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()
                async with session.get(url, headers=headers, timeout=30, proxy=self.get_request_proxy()) as response:
                    if response.status == 403:
                        logger.error("SecurityTrails API key is invalid or limit reached.")
                        return
                    if response.status != 200:
                        logger.error(f"SecurityTrails returned status {response.status}")
                        return

                    data = await response.json()
                    subdomains: Set[str] = set()
                    
                    for sub in data.get("subdomains", []):
                        full_domain = f"{sub}.{target}".lower()
                        subdomains.add(full_domain)

                    findings = [{"subdomain": sub, "source": "securitytrails"} for sub in sorted(list(subdomains))]
                    
                    if findings:
                        self.store_results(target, "securitytrails", findings)
                        logger.info(f"Found {len(findings)} subdomains for {target} via SecurityTrails")
                    else:
                        logger.info(f"No subdomains found for {target} via SecurityTrails")

        except Exception as e:
            import traceback
            logger.error(f"Error querying SecurityTrails: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting SecurityTrails.run for target: {target}")

