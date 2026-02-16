from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from .api import api_router, add_exception_handlers
from .websocket_manager import WebSocketManager
from .scan_manager import ScanManager
import os
import logging
import asyncio
import sys

# Ensure ProactorEventLoop is used on Windows for subprocess support (needed for Playwright)
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="ReconMaster Web Dashboard")
add_exception_handlers(app)

# Initialize Managers
ws_manager = WebSocketManager()
scan_manager = ScanManager(ws_manager)

# Store in app state for dependency injection
app.state.scan_manager = scan_manager
app.state.ws_manager = ws_manager

# Mount static files
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)
app.mount("/static", StaticFiles(directory=static_dir), name="static")

# Mount reports directory for screenshots
reports_dir = os.path.join(os.getcwd(), "reports")
if not os.path.exists(reports_dir):
    os.makedirs(reports_dir)
app.mount("/reports", StaticFiles(directory=reports_dir), name="reports")

# Jinja2 templates
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
if not os.path.exists(templates_dir):
    os.makedirs(templates_dir)
templates = Jinja2Templates(directory=templates_dir)

# Include API router
app.include_router(api_router, prefix="/api")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- View Routes ---

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/scan/{scan_id}")
async def scan_progress(request: Request, scan_id: str):
    # Verify scan exists? Optional, but good UX.
    scan = await scan_manager.get_scan(scan_id)
    if not scan:
        return templates.TemplateResponse("index.html", {"request": request, "error": "Scan not found"})
    return templates.TemplateResponse("scan.html", {"request": request, "scan_id": scan_id, "scan": scan})

@app.get("/results/{target}")
async def results_page(request: Request, target: str, scan_id: Optional[str] = None):
    return templates.TemplateResponse("results.html", {"request": request, "target": target, "scan_id": scan_id})

# --- WebSocket ---

@app.websocket("/ws/{scan_id}")
async def websocket_endpoint(websocket: WebSocket, scan_id: str):
    await ws_manager.connect(scan_id, websocket)
    try:
        # Send history
        history = scan_manager.get_scan_logs(scan_id)
        for msg in history:
            await websocket.send_json(msg)
            
        while True:
            # Keep connection alive, maybe handle client messages if needed
            data = await websocket.receive_text()
            # We don't really expect client messages for now
    except WebSocketDisconnect:
        await ws_manager.disconnect(scan_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await ws_manager.disconnect(scan_id, websocket)
