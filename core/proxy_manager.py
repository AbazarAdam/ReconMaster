import logging
from typing import Optional, Dict, Any
import aiohttp
from aiohttp_socks import ProxyConnector

logger = logging.getLogger(__name__)

class ProxyManager:
    """
    Manages proxies and Tor support for aiohttp requests.
    """
    def __init__(self, config: Dict[str, Any]):
        self.http_proxy = config.get("http")
        self.https_proxy = config.get("https")
        self.use_tor = config.get("use_tor", False)
        self.tor_proxy = "socks5://127.0.0.1:9050" if self.use_tor else None

    def get_connector(self) -> Optional[aiohttp.BaseConnector]:
        """
        Returns a connector with proxy support if configured.
        """
        proxy_url = self.tor_proxy or self.https_proxy or self.http_proxy
        
        if proxy_url:
            if proxy_url.startswith("socks"):
                logger.info(f"Using SOCKS proxy: {proxy_url}")
                return ProxyConnector.from_url(proxy_url)
            else:
                logger.info(f"Using HTTP proxy: {proxy_url}")
                # HTTP proxies can be used directly in session.get,
                # but if we want a global connector:
                return aiohttp.TCPConnector()
        
        return None

    def get_proxy_url(self) -> Optional[str]:
        """
        Returns the proxy URL to be passed to aiohttp request methods.
        """
        # SOCKS proxies are handled by the connector, so we return None here
        # to avoid double proxying if a ProxyConnector is used.
        proxy_url = self.tor_proxy or self.https_proxy or self.http_proxy
        if proxy_url and not proxy_url.startswith("socks"):
            return proxy_url
        return None
