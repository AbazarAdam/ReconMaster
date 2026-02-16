import asyncio
import logging
from github import Github, GithubException
from typing import List, Dict, Any
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class GithubDorker(BaseModule):
    @property
    def name(self) -> str:
        return "dorker"

    @property
    def module_type(self) -> str:
        return "github"

    async def run(self, target: str):
        """
        Searches GitHub for secrets and exposed code related to the target domain.
        """
        logger.debug(f"[MODULE DEBUG] Entering GithubDorker.run for target: {target}")
        try:
            token = self.config.get("api_keys", {}).get("github")
            g = Github(token) if token else Github()
            
            dork_templates = self.config.get("dorks", [
                '"{domain}"', 
                '"{domain}" api_key', 
                '"{domain}" secret'
            ])
            
            findings = []
            logger.info(f"Starting GitHub dorking for {target}...")

            base_domain = target # or extract base domain if needed
            
            for template in dork_templates:
                query = template.format(domain=base_domain)
                logger.info(f"Running GitHub query: {query}")
                
                if self.limiter:
                    await self.limiter.acquire()
                
                try:
                    # PyGithub is blocking, use to_thread
                    # Search code can be very rate-limited
                    results = await asyncio.to_thread(g.search_code, query)
                    
                    # Limit to top 10 results per dork for now
                    count = 0
                    for file in results:
                        if count >= 10:
                            break
                        
                        findings.append({
                            "query": query,
                            "url": file.html_url,
                            "repository": file.repository.full_name,
                            "path": file.path
                        })
                        count += 1
                    
                    logger.info(f"Found {count} results for dork: {query}")

                except GithubException as e:
                    if e.status == 403:
                        logger.warning("GitHub API rate limit reached or search disabled/forbidden.")
                        break
                    logger.error(f"GitHub API error for query '{query}': {e}")
                except Exception as e:
                    logger.error(f"Unexpected error dorking GitHub: {e}")

            if findings:
                self.store_results(target, "github_dorker", "github", findings)
                logger.info(f"Stored {len(findings)} GitHub dorking results")
            else:
                logger.info(f"No sensitive GitHub results found for {target}")
        except Exception as e:
            import traceback
            logger.error(f"GithubDorker failed for {target}: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting GithubDorker.run for target: {target}")

