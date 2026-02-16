import re
import logging
from typing import List, Any, Dict

logger = logging.getLogger(__name__)

def is_valid_domain(domain: str) -> bool:
    """
    Checks if a string is a valid domain name.
    """
    pattern = r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$"
    return bool(re.match(pattern, domain.lower()))

def deduplicate_results(entries: List[Dict[str, Any]], key: str) -> List[Dict[str, Any]]:
    """
    Deduplicates a list of dictionaries based on a specific key.
    """
    seen = set()
    deduped = []
    for entry in entries:
        val = str(entry.get(key, ""))
        if val not in seen:
            seen.add(val)
            deduped.append(entry)
    return deduped

def extract_subdomains(target: str, text: str) -> List[str]:
    """
    Extracts subdomains of a target from a blob of text.
    """
    # Simple regex for domains ending with the target
    pattern = rf"([a-z0-9.-]+\.{re.escape(target)})"
    matches = re.findall(pattern, text.lower())
    return sorted(list(set(matches)))
