from fastapi import WebSocket
from typing import Dict, List
import logging
import json

logger = logging.getLogger(__name__)

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, scan_id: str, websocket: WebSocket):
        await websocket.accept()
        if scan_id not in self.active_connections:
            self.active_connections[scan_id] = []
        self.active_connections[scan_id].append(websocket)
        logger.info(f"WebSocket connected for scan {scan_id}")

    async def disconnect(self, scan_id: str, websocket: WebSocket):
        if scan_id in self.active_connections:
            if websocket in self.active_connections[scan_id]:
                self.active_connections[scan_id].remove(websocket)
            if not self.active_connections[scan_id]:
                del self.active_connections[scan_id]
        logger.info(f"WebSocket disconnected for scan {scan_id}")

    async def send_message(self, scan_id: str, message: dict):
        if scan_id in self.active_connections:
            # Broadcast to all connected clients for this scan
            to_remove = []
            for connection in self.active_connections[scan_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to client: {e}")
                    to_remove.append(connection)
            
            # Cleanup dead connections
            for connection in to_remove:
                await self.disconnect(scan_id, connection)
