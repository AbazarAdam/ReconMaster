import logging
import re
from typing import Any, Dict, List, Set

logger = logging.getLogger(__name__)


def is_valid_domain(domain: str) -> bool:
    """Validates if a string follows the standard domain name format.

    Uses a strict regex pattern to check for valid characters and structure.

    Args:
        domain: The domain string to validate.

    Returns:
        True if the domain is valid, False otherwise.
    """
    pattern = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$"
    return bool(re.match(pattern, domain.lower()))


def deduplicate_results(entries: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """Removes duplicate dictionaries from a list based on a specific key value.

    Args:
        entries: A list of dictionaries to process.
        key: The dictionary key to check for uniqueness.

    Returns:
        A new list containing only unique dictionary entries.
    """
    seen: Set[str] = set()
    deduped: List[Dict[str, Any]] = []
    for entry in entries:
        val = str(entry.get(key, ""))
        if val not in seen:
            seen.add(val)
            deduped.append(entry)
    return deduped


def extract_subdomains(target: str, text: str) -> List[str]:
    """Passes a blob of text and extracts strings matching subdomains of the target.

    Args:
        target: The base domain (e.g., 'example.com').
        text: The raw text data to search through.

    Returns:
        A sorted list of unique subdomain strings discovered in the text.
    """
    # Regex pattern for domains ending with the target domain
    pattern = rf"([a-z0-9.-]+\.{re.escape(target)})"
    matches = re.findall(pattern, text.lower())
    return sorted(list(set(matches)))
