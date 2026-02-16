import logging
from typing import Any, Dict, Optional

import aiohttp
from aiohttp_socks import ProxyConnector

logger = logging.getLogger(__name__)


class ProxyManager:
    """Manages HTTP, HTTPS, and Tor (SOCKS5) proxy configurations.

    This manager centralizes proxy logic for aiohttp sessions, ensuring that
    module-level requests correctly route through the configured gateway.

    Attributes:
        http_proxy: URL for the HTTP proxy.
        https_proxy: URL for the HTTPS proxy.
        use_tor: Boolean flag to enable Tor routing.
        tor_proxy: The default Tor SOCKS5 endpoint.
    """

    def __init__(self, config: Dict[str, Any]):
        """Initializes the ProxyManager with settings from the configuration.

        Args:
            config: A dictionary containing 'http', 'https', and 'use_tor' keys.
        """
        self.http_proxy = config.get("http")
        self.https_proxy = config.get("https")
        self.use_tor = config.get("use_tor", False)
        self.tor_proxy = "socks5://127.0.0.1:9050" if self.use_tor else None

    def get_connector(self) -> Optional[aiohttp.BaseConnector]:
        """Creates an aiohttp connector with proxy support.

        If a SOCKS proxy (like Tor) is configured, it returns a ProxyConnector.
        For standard HTTP proxies, it returns a standard TCPConnector (as HTTP
        proxies are typically handled at the request level).

        Returns:
            An aiohttp compatible connector or None if no proxy is configured.
        """
        proxy_url = self.tor_proxy or self.https_proxy or self.http_proxy

        if proxy_url:
            if proxy_url.startswith("socks"):
                logger.info(f"[PROXY] Initializing SOCKS connector: {proxy_url}")
                return ProxyConnector.from_url(proxy_url)
            else:
                logger.info(f"[PROXY] Initializing TCP connector for HTTP proxy: {proxy_url}")
                return aiohttp.TCPConnector()

        return None

    def get_proxy_url(self) -> Optional[str]:
        """Retrieves the HTTP/HTTPS proxy URL for request-level routing.

        SOCKS proxies are excluded here as they must be handled by the connector
        to avoid redundant or conflicting proxy calls.

        Returns:
            The proxy URL string or None if not applicable.
        """
        proxy_url = self.tor_proxy or self.https_proxy or self.http_proxy
        if proxy_url and not proxy_url.startswith("socks"):
            return proxy_url
        return None
