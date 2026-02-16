import aiohttp
import asyncio
import logging
import json
from typing import List, Dict, Any, Set
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class CertificateTransparency(BaseModule):
    @property
    def name(self) -> str:
        return "ct"

    @property
    def module_type(self) -> str:
        return "subdomain"

    async def run(self, target: str):
        """
        Fetches subdomains from crt.sh for a given target.
        URL: https://crt.sh/?q=%.{target}&output=json
        """
        logger.debug(f"[MODULE DEBUG] Entering CertificateTransparency.run for target: {target}")
        if not self.validate_target(target):
            logger.error(f"Invalid target: {target}")
            return

        url = f"https://crt.sh/?q=%.{target}&output=json"
        logger.info(f"Searching crt.sh for {target}...")
        try:
            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                if self.limiter:
                    await self.limiter.acquire()
                
                async with session.get(url, timeout=30, proxy=self.get_request_proxy()) as response:
                    if response.status != 200:
                        logger.error(f"crt.sh returned status {response.status}")
                        return

                    try:
                        data = await response.json()
                    except aiohttp.ContentTypeError:
                        # Sometimes crt.sh returns text even if json is requested if it's an error page
                        text = await response.text()
                        logger.error(f"Failed to parse JSON from crt.sh. Response: {text[:200]}")
                        return

                    subdomains: Set[str] = set()
                    for entry in data:
                        name_value = entry.get("name_value", "")
                        # name_value can contain multiple domains separated by newline
                        for domain in name_value.split("\n"):
                            domain = domain.strip().lower()
                            # Clean wildcard and ensure it ends with our target
                            if domain.startswith("*."):
                                domain = domain[2:]
                            
                            if domain.endswith(target) and domain != target:
                                subdomains.add(domain)

                    findings = [{"subdomain": sub, "source": "crt.sh"} for sub in sorted(list(subdomains))]
                    
                    if findings:
                        self.store_results(target, "crt.sh", "subdomain", findings)
                        logger.info(f"Found {len(findings)} subdomains for {target} via crt.sh")
                    else:
                        logger.info(f"No subdomains found for {target} via crt.sh")

        except asyncio.TimeoutError:
            logger.error(f"Timeout while query crt.sh for {target}")
        except Exception as e:
            import traceback
            logger.error(f"Error querying crt.sh: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting CertificateTransparency.run for target: {target}")
