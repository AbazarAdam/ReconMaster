import asyncio
import socket
import logging
from typing import List, Dict, Any
from core.module_loader import BaseModule

logger = logging.getLogger(__name__)

class PortScanner(BaseModule):
    @property
    def name(self) -> str:
        return "scanner"

    @property
    def module_type(self) -> str:
        return "portscan"

    async def run(self, target: str):
        """
        Scans common ports for the target.
        Resolves domain to IP and then scans.
        """
        logger.debug(f"[MODULE DEBUG] Entering PortScanner.run for target: {target}")
        try:
            try:
                ip = socket.gethostbyname(target)
                logger.info(f"Resolved {target} to {ip}. Starting port scan...")
            except socket.gaierror:
                logger.error(f"Could not resolve target: {target}")
                return

            ports = self.config.get("ports", [21,22,23,25,53,80,110,111,135,139,143,443,445,993,995,1723,3306,3389,5900,8080,8443])
            timeout = self.config.get("timeout", 2)
            concurrency = self.config.get("concurrency", 100)
            
            semaphore = asyncio.Semaphore(concurrency)
            
            async def check_port(port):
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

            tasks = [check_port(port) for port in ports]
            results = await asyncio.gather(*tasks)
            
            open_ports = [p for p in results if p is not None]
            
            if open_ports:
                findings = [{"ip": ip, "port": p, "state": "open"} for p in open_ports]
                self.store_results(target, "port_scanner", "port", findings)
                logger.info(f"Found {len(open_ports)} open ports for {target}")
            else:
                logger.info(f"No open ports found for {target}")
        except Exception as e:
            import traceback
            logger.error(f"Port scan failed for {target}: {e}")
            logger.error(traceback.format_exc())
        finally:
            logger.debug(f"[MODULE DEBUG] Exiting PortScanner.run for target: {target}")
