import asyncio
import logging
from typing import Any, Dict, List, Optional

import aiohttp

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class CloudBucketEnumerator(BaseModule):
    """Enumerates potential public storage buckets across AWS, Azure, and GCP.

    Uses a wordlist of common naming patterns derived from the target domain.
    Attempts to identify public (read/list) and private (denied but existing) buckets.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "enumerator"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "cloud_buckets"

    async def run(self, target: str) -> None:
        """Main execution logic for the Cloud Bucket module.

        Args:
            target: The domain to generate bucket names from.
        """
        try:
            # Load templates and providers from configuration
            wordlist_templates = self.config.get(
                "wordlist",
                ["{domain}", "{domain}-backup", "{domain}-assets", "backup-{domain}"],
            )
            providers = self.config.get("providers", ["aws", "azure", "gcp"])

            # Clean domain for template formatting
            domain_name = target.split(".")[0]
            bucket_names = [t.format(domain=domain_name) for t in wordlist_templates]

            logger.info(
                f"[CLOUD] Checking {len(bucket_names)} patterns across {len(providers)} providers..."
            )

            async with aiohttp.ClientSession(**self.get_session_kwargs()) as session:
                tasks = []
                for name in bucket_names:
                    for provider in providers:
                        tasks.append(self.check_bucket(session, name, provider))

                results = await asyncio.gather(*tasks)
                findings = [f for f in results if f is not None]

            if findings:
                self.store_results(
                    target, "cloud_bucket_enumerator", "cloud_bucket", findings
                )
                logger.info(f"[CLOUD] Successfully identified {len(findings)} buckets")
            else:
                logger.info(f"[CLOUD] No public buckets discovered for {target}")

        except Exception as e:
            logger.error(f"[CLOUD] Enumeration failed: {e}")

    async def check_bucket(
        self, session: aiohttp.ClientSession, name: str, provider: str
    ) -> Optional[Dict[str, Any]]:
        """Probes a single bucket endpoint to determine existence and permissions.

        Args:
            session: An active aiohttp session.
            name: The bucket name to check.
            provider: The cloud provider string ('aws', 'azure', or 'gcp').

        Returns:
            A dictionary containing bucket details if found, else None.
        """
        if self.limiter:
            await self.limiter.acquire()

        # Construct provider-specific URL
        url = ""
        if provider == "aws":
            url = f"https://{name}.s3.amazonaws.com"
        elif provider == "azure":
            url = f"https://{name}.blob.core.windows.net/"
        elif provider == "gcp":
            url = f"https://storage.googleapis.com/{name}/"

        if not url:
            return None

        try:
            # Use HEAD request for efficiency (check status without downloading content)
            async with session.head(
                url, timeout=5, allow_redirects=True, proxy=self.get_request_proxy()
            ) as response:
                if response.status in [200, 403]:
                    # 200 = Publicly accessible, 403 = Exists but access denied
                    return {
                        "bucket": name,
                        "provider": provider,
                        "url": url,
                        "status": "public" if response.status == 200 else "private",
                    }
        except Exception:
            pass  # Silently ignore connection errors (bucket likely doesn't exist)
        return None
