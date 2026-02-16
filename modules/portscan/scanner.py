import asyncio
import logging
import socket
from typing import Any, Dict, List, Optional

from core.module_loader import BaseModule

logger = logging.getLogger(__name__)


class PortScanner(BaseModule):
    """An asynchronous TCP port scanner for identifying active services.

    Resolves the target domain to an IP address and probes a configurable list
    of common ports. Uses semaphores to control concurrency.
    """

    @property
    def name(self) -> str:
        """The module name."""
        return "scanner"

    @property
    def module_type(self) -> str:
        """The module category."""
        return "portscan"

    async def run(self, target: str) -> None:
        """Main execution logic for the Port Scanner module.

        Args:
            target: The domain or IP to scan.
        """
        try:
            # Resolve domain to IP (OS-level resolution)
            try:
                ip = await asyncio.to_thread(socket.gethostbyname, target)
                logger.info(f"[PORTSCAN] Resolved {target} to {ip}. Initiating scan...")
            except socket.gaierror:
                logger.error(f"[PORTSCAN] Failed to resolve target: {target}")
                return

            # Load scan parameters from configuration
            ports = self.config.get(
                "ports",
                [
                    21, 22, 23, 25, 53, 80, 110, 111, 135, 139, 143, 443, 445, 993, 
                    995, 1723, 3306, 3389, 5900, 8080, 8443
                ],
            )
            timeout = self.config.get("timeout", 2)
            concurrency = self.config.get("concurrency", 100)

            semaphore = asyncio.Semaphore(concurrency)

            async def check_port(port: int) -> Optional[int]:
                """Attempts to establish a TCP connection to a specific port."""
                async with semaphore:
                    if self.limiter:
                        await self.limiter.acquire()
                    try:
                        conn = asyncio.open_connection(ip, port)
                        _, writer = await asyncio.wait_for(conn, timeout=timeout)
                        writer.close()
                        await writer.wait_closed()
                        return port
                    except (asyncio.TimeoutError, ConnectionRefusedError, OSError):
                        return None

            tasks = [check_port(p) for p in ports]
            results = await asyncio.gather(*tasks)

            open_ports = [p for p in results if p is not None]

            if open_ports:
                findings = [{"ip": ip, "port": p, "state": "open"} for p in open_ports]
                self.store_results(target, "port_scanner", "port", findings)
                logger.info(f"[PORTSCAN] Discovered {len(open_ports)} open ports")
            else:
                logger.info(f"[PORTSCAN] No common ports found open for {target}")

        except Exception as e:
            logger.error(f"[PORTSCAN] Module execution failed: {e}")
