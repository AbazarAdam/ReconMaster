from fastapi import APIRouter, HTTPException, status, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Any
import re
import sys
from .scan_manager import ScanManager
from .websocket_manager import WebSocketManager

api_router = APIRouter()

# Dependency dependency injection pattern would be better, but we'll use a global instance for now
# initialized in app.py and imported here? Or initialized here?
# Better to initialize in app.py and pass it, but FastAPI routers make that tricky without dependency overrides.
# We will rely on app.state or a global singleton if possible. 
# For simplicity in this structure: initialization happens in app.py, but we need access here.
# We'll expect the app to inject it or we create a lazy loader.

# To avoid circular imports, we'll access via request.app.state if we can, OR 
# we create a singleton instance in a separate module. 
# Let's assume ScanManager is initialized in app.py and we can get it via a dependency.

async def get_scan_manager(request: Request) -> ScanManager:
    return request.app.state.scan_manager

class ScanRequest(BaseModel):
    target: str = Field(..., description="Target domain", example="example.com")
    config: Optional[dict] = None

    @validator("target")
    def validate_target(cls, v):
        # weak regex but simple
        pattern = r"^[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(pattern, v):
            raise ValueError("Invalid domain format.")
        return v

class ScanResponse(BaseModel):
    scan_id: str
    status: str

@api_router.post("/scans", response_model=ScanResponse, status_code=201)
async def start_scan(scan: ScanRequest, manager: ScanManager = Depends(get_scan_manager)):
    try:
        scan_id = await manager.start_scan(scan.target, scan.config)
        return ScanResponse(scan_id=scan_id, status="pending")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/scans", response_model=List[dict])
async def list_scans(manager: ScanManager = Depends(get_scan_manager)):
    return await manager.list_scans()

@api_router.get("/scans/{scan_id}")
async def get_scan(scan_id: str, manager: ScanManager = Depends(get_scan_manager)):
    scan = await manager.get_scan(scan_id)
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found")
    return scan

@api_router.get("/scans/{scan_id}/results")
async def get_scan_results(scan_id: str, manager: ScanManager = Depends(get_scan_manager)):
    results = await manager.get_scan_results(scan_id)
    return results

@api_router.get("/diag")
async def get_diagnostic(request: Request):
    import os
    from pathlib import Path
    return {
        "status": "online",
        "cwd": os.getcwd(),
        "db_exists": os.path.exists("recon.db"),
        "reports_writable": os.access("reports", os.W_OK) if os.path.exists("reports") else False,
        "python_version": sys.version.split()[0]
    }

@api_router.get("/targets/{target}/results")
async def get_target_results(target: str, manager: ScanManager = Depends(get_scan_manager)):
    results = await manager.get_target_results(target)
    return results

@api_router.post("/scans/clear")
async def clear_history(manager: ScanManager = Depends(get_scan_manager)):
    try:
        await manager.clear_history()
        return {"status": "success", "message": "History cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def add_exception_handlers(app):
    from fastapi.exceptions import RequestValidationError
    
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc)},
        )
