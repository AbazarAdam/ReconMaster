from core.database import Database
import asyncio
from typing import List, Dict, Any, Optional

class AsyncDatabase:
    """
    Async wrapper around the synchronous core.database.Database class.
    Uses asyncio.to_thread to run blocking SQLite operations in a separate thread.
    """
    def __init__(self, db_path: str = "recon.db"):
        self.db = Database(db_path)

    async def get_scans(self, limit: int = 50) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.db.get_scans, limit)

    async def get_scan(self, scan_id: str) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self.db.get_scan, scan_id)

    async def get_results(self, target: str, module: Optional[str] = None, scan_id: Optional[str] = None) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.db.get_results, target, module, scan_id)

    async def get_unique_results(self, target: str, result_type: str) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self.db.get_unique_results, target, result_type)

    async def create_scan(self, scan_id: str, target: str, status: str = "pending"):
        await asyncio.to_thread(self.db.create_scan, scan_id, target, status)

    async def update_scan_status(self, scan_id: str, status: str):
        await asyncio.to_thread(self.db.update_scan_status, scan_id, status)
    async def clear_history(self):
        await asyncio.to_thread(self.db.clear_history)
