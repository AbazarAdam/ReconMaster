import asyncio
import logging
from typing import Any, Dict, List

from github import Github, GithubException

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class GithubDorker(BaseModule):
    """Searches GitHub for potential secrets, configurations, and exposed code.

    Uses customizable dork templates to scan for files related to the target domain.
    Utilizes the 'PyGithub' library for API interaction.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "dorker"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "github"

    async def run(self, target: str) -> None:
        """Main execution logic for the GitHub Dorker module.

        Args:
            target: The domain/organization to dork for.
        """
        try:
            # Initialize GitHub client (optional token for higher rate limits)
            token = self.config.get("api_keys", {}).get("github")
            g = Github(token) if token else Github()

            # Load dork templates from config or use defaults
            dork_templates = self.config.get(
                "dorks", ['"{domain}"', '"{domain}" api_key', '"{domain}" secret']
            )

            findings = []
            logger.info(f"[GITHUB] Initiating search for {target}...")

            for template in dork_templates:
                query = template.format(domain=target)
                logger.info(f"[GITHUB] Executing dork: {query}")

                if self.limiter:
                    await self.limiter.acquire()

                try:
                    # PyGithub is synchronous/blocking; offload to a thread
                    results = await asyncio.to_thread(g.search_code, query)

                    # Limit to top 10 results per dork to avoid excessive noise/limits
                    count = 0
                    for file in results:
                        if count >= 10:
                            break

                        findings.append(
                            {
                                "query": query,
                                "url": file.html_url,
                                "repository": file.repository.full_name,
                                "path": file.path,
                            }
                        )
                        count += 1

                    logger.debug(f"[GITHUB] Found {count} results for: {query}")

                except GithubException as e:
                    if e.status == 403:
                        logger.warning(
                            "[GITHUB] Rate limit hit or search is forbidden for this account"
                        )
                        break
                    logger.error(f"[GITHUB] API error for query '{query}': {e}")
                except Exception as e:
                    logger.error(f"[GITHUB] Unexpected dorking error: {e}")

            if findings:
                self.store_results(target, "github_dorker", "github", findings)
                logger.info(f"[GITHUB] Successfully stored {len(findings)} dork results")
            else:
                logger.info(f"[GITHUB] No exposure discovered for {target}")

        except Exception as e:
            logger.error(f"[GITHUB] Module execution failed: {e}")

