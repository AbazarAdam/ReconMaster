import asyncio
import uuid
import logging
import traceback
from typing import Dict, Any, List
from .websocket_manager import WebSocketManager
from .db import AsyncDatabase
from core.engine import run_scan as core_run_scan

logger = logging.getLogger(__name__)

class ScanManager:
    def __init__(self, ws_manager: WebSocketManager):
        self.ws_manager = ws_manager
        self.db = AsyncDatabase()
        # Keep track of running tasks if needed (optional)
        self.active_scans: Dict[str, asyncio.Task] = {}
        self.scan_logs: Dict[str, List[dict]] = {}

    async def start_scan(self, target: str, config: dict = None) -> str:
        scan_id = str(uuid.uuid4())
        self.scan_logs[scan_id] = []
        
        # Define progress callback
        async def progress_callback(data: dict):
            # store log
            if scan_id in self.scan_logs:
                self.scan_logs[scan_id].append(data)
                # Keep last 1000 logs
                if len(self.scan_logs[scan_id]) > 1000:
                    self.scan_logs[scan_id] = self.scan_logs[scan_id][-1000:]
            
            # Send to WebSocket
            await self.ws_manager.send_message(scan_id, data)
        
        # Pre-create scan record to avoid race conditions (404/500 errors)
        await self.db.create_scan(scan_id, target, status="pending")

        # Create task
        task = asyncio.create_task(self._run_background_scan(scan_id, target, config, progress_callback))
        self.active_scans[scan_id] = task
        
        return scan_id

    def get_scan_logs(self, scan_id: str) -> List[dict]:
        return self.scan_logs.get(scan_id, [])

    async def _run_background_scan(self, scan_id: str, target: str, config: dict, callback):
        try:
            # The core engine now handles DB creation for the scan record if scan_id is passed
            # But we should probably ensure it exists before starting, or let the engine do it.
            # Engine does: db.create_scan(scan_id, target, "running")
            
            await core_run_scan(target, scan_id=scan_id, progress_callback=callback)
            
        except Exception as e:
            logger.error(f"Error in background scan {scan_id}: {traceback.format_exc()}")
            await callback({"type": "error", "message": str(e)})
        finally:
            if scan_id in self.active_scans:
                del self.active_scans[scan_id]

    async def list_scans(self) -> List[Dict[str, Any]]:
        return await self.db.get_scans()

    async def get_scan(self, scan_id: str) -> Dict[str, Any]:
        return await self.db.get_scan(scan_id)
    
    async def get_scan_results(self, scan_id: str) -> List[Dict[str, Any]]:
        scan = await self.db.get_scan(scan_id)
        if not scan:
            return []
        return await self.db.get_results(scan['target'], scan_id=scan_id)
    
    async def get_target_results(self, target: str) -> List[Dict[str, Any]]:
        return await self.db.get_results(target)
    async def clear_history(self):
        await self.db.clear_history()
        self.scan_logs.clear()
        logger.info("Scan history and logs cleared")
