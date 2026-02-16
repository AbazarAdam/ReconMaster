import aiohttp
import logging
from typing import Set
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class Anubis(BaseModule):
    @property
    def name(self) -> str:
        return "anubis"

    @property
    def module_type(self) -> str:
        return "subdomain"

    async def run(self, target: str):
        """
        Fetches subdomains from AnubisDB.
        URL: https://jldc.me/anubis/subdomains/{target}
        """
        logger.debug(f"[MODULE DEBUG] Entering Anubis.run for target: {target}")
        if not self.validate_target(target):
            logger.error(f"Invalid target: {target}")
            return

        url = f"https://jldc.me/anubis/subdomains/{target}"
        logger.info(f"Searching Anubis for {target}...")

        try:
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()
                async with session.get(url, timeout=30, proxy=self.get_request_proxy()) as response:
                    if response.status != 200:
                        logger.error(f"Anubis returned status {response.status}")
                        return

                    data = await response.json()
                    subdomains: Set[str] = set()
                    
                    if isinstance(data, list):
                        for sub in data:
                            sub = sub.lower().strip()
                            if sub.endswith(target) and sub != target:
                                subdomains.add(sub)

                    findings = [{"subdomain": sub, "source": "anubis"} for sub in sorted(list(subdomains))]
                    
                    if findings:
                        self.store_results(target, "anubis", findings)
                        logger.info(f"Found {len(findings)} subdomains for {target} via Anubis")
                    else:
                        logger.info(f"No subdomains found for {target} via Anubis")

        except Exception as e:
            import traceback
            logger.error(f"Error querying Anubis: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting Anubis.run for target: {target}")

