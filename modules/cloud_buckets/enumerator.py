import asyncio
import logging
import aiohttp
from typing import List, Dict, Any, Optional
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class CloudBucketEnumerator(BaseModule):
    @property
    def name(self) -> str:
        return "enumerator"

    @property
    def module_type(self) -> str:
        return "cloud_buckets"

    async def run(self, target: str):
        """
        Enumerates cloud storage buckets for AWS, Azure, and GCP.
        """
        logger.debug(f"[MODULE DEBUG] Entering CloudBucketEnumerator.run for target: {target}")
        try:
            wordlist_templates = self.config.get("wordlist", [
                "{domain}", "{domain}-backup", "{domain}-assets", "backup-{domain}"
            ])
            providers = self.config.get("providers", ["aws", "azure", "gcp"])
            
            domain_name = target.split('.')[0]
            bucket_names = [t.format(domain=domain_name) for t in wordlist_templates]
            
            findings = []
            logger.info(f"Enumerating {bucket_names} bucket names for {len(providers)} providers...")

            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                tasks = []
                for name in bucket_names:
                    for provider in providers:
                        tasks.append(self.check_bucket(session, name, provider))
                
                results = await asyncio.gather(*tasks)
                findings = [f for f in results if f is not None]

            if findings:
                self.store_results(target, "cloud_bucket_enumerator", "cloud_bucket", findings)
                logger.info(f"Found {len(findings)} potentially public cloud buckets")
            else:
                logger.info(f"No public cloud buckets found for {target}")
        except Exception as e:
            import traceback
            logger.error(f"CloudBucketEnumerator failed for {target}: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting CloudBucketEnumerator.run for target: {target}")

    async def check_bucket(self, session: aiohttp.ClientSession, name: str, provider: str) -> Optional[Dict[str, Any]]:
        if self.limiter:
            await self.limiter.acquire()

        url = ""
        if provider == "aws":
            url = f"https://{name}.s3.amazonaws.com"
        elif provider == "azure":
            url = f"https://{name}.blob.core.windows.net/"
        elif provider == "gcp":
            url = f"https://storage.googleapis.com/{name}/"
        
        try:
            # We use a HEAD request to check existence and status
            async with session.head(url, timeout=5, allow_redirects=True, proxy=self.get_request_proxy()) as response:
                if response.status in [200, 403]:
                    # 200: Public, 403: Exists but Private
                    return {
                        "bucket": name,
                        "provider": provider,
                        "url": url,
                        "status": "public" if response.status == 200 else "private"
                    }
        except Exception:
            pass
        return None

