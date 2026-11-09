import os
import shutil
import asyncio
import logging
from pathlib import Path
from typing import Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.scanner import StorageScanner
from app.cleaner import run_retention_cleanup

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("reoftpview")

# Configuration from Environment Variables
RECORDINGS_PATH = os.environ.get("RECORDINGS_PATH", "/recordings")
RETENTION_DAYS = int(os.environ.get("RETENTION_DAYS", "30"))
CLEANUP_INTERVAL_HOURS = int(os.environ.get("CLEANUP_INTERVAL_HOURS", "6"))
CACHE_PATH = os.environ.get("CACHE_PATH", "/tmp/reoftpview_cache")

scanner = StorageScanner(RECORDINGS_PATH, CACHE_PATH)

async def periodic_cleanup_task():
    """Background task running retention cleanup every N hours."""
    while True:
        try:
            logger.info("Triggering scheduled retention cleanup...")
            run_retention_cleanup(RECORDINGS_PATH, RETENTION_DAYS)
        except Exception as e:
            logger.error(f"Error during periodic cleanup: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL_HOURS * 3600)

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting ReoFTPView. Recordings: {RECORDINGS_PATH}, Retention: {RETENTION_DAYS} days.")
    # Run initial cleanup in background
    asyncio.create_task(run_retention_cleanup_async())
    # Start periodic loop
    cleanup_task = asyncio.create_task(periodic_cleanup_task())
    yield
    cleanup_task.cancel()

async def run_retention_cleanup_async():
    await asyncio.to_thread(run_retention_cleanup, RECORDINGS_PATH, RETENTION_DAYS)

app = FastAPI(title="ReoFTPView", lifespan=lifespan)

# Templates
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# --- Page Routes ---
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "retention_days": RETENTION_DAYS,
        "recordings_path": RECORDINGS_PATH
    })

# --- API Routes ---
@app.get("/api/status")
async def get_status():
    """Get system storage status and settings."""
    total, used, free = 0, 0, 0
    try:
        usage = shutil.disk_usage(RECORDINGS_PATH)
        total, used, free = usage.total, usage.used, usage.free
    except Exception:
        pass

    return {
        "recordings_path": RECORDINGS_PATH,
        "retention_days": RETENTION_DAYS,
        "cleanup_interval_hours": CLEANUP_INTERVAL_HOURS,
        "storage": {
            "total_gb": round(total / (1024**3), 1),
            "used_gb": round(used / (1024**3), 1),
            "free_gb": round(free / (1024**3), 1),
            "used_pct": round((used / total * 100), 1) if total > 0 else 0
        }
    }

@app.get("/api/cameras")
async def list_cameras():
    """Return all camera directories and total video counts."""
    return scanner.get_cameras()

@app.get("/api/cameras/{camera_id}/dates")
async def list_camera_dates(camera_id: str):
    """Return all dates (YYYY-MM-DD) with recordings for this camera."""
    return scanner.get_available_dates(camera_id)

@app.get("/api/cameras/{camera_id}/recordings")
async def list_recordings(camera_id: str, date: str = Query(..., regex=r"^\d{4}-\d{2}-\d{2}$")):
    """Return all video recordings for a camera on a specific date."""
    return scanner.get_recordings_for_date(camera_id, date)

@app.get("/api/stream/{rel_path:path}")
async def stream_video(rel_path: str):
    """
    Stream MP4 video directly with full HTTP Range request support.
    HTML5 video player seeks seamlessly without full download or transcoding!
    """
    abs_path = scanner.get_absolute_path(rel_path)
    if not abs_path or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")

    return FileResponse(
        path=str(abs_path),
        media_type="video/mp4",
        filename=abs_path.name
    )

@app.get("/api/thumb/{rel_path:path}")
async def get_thumbnail(rel_path: str):
    """Serve companion JPG or generate frame via FFmpeg."""
    abs_path = scanner.get_absolute_path(rel_path)
    if not abs_path or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    thumb_path = await asyncio.to_thread(scanner.get_or_create_thumbnail, abs_path)
    if thumb_path and thumb_path.exists():
        return FileResponse(path=str(thumb_path), media_type="image/jpeg")

    # Fallback default empty or 404
    raise HTTPException(status_code=404, detail="Thumbnail could not be generated")

@app.delete("/api/recording/{rel_path:path}")
async def delete_recording(rel_path: str):
    """Delete a recording and its companion thumbnail."""
    abs_path = scanner.get_absolute_path(rel_path)
    if not abs_path or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="Recording not found")

    try:
        # Delete video
        abs_path.unlink()
        # Delete companion thumbnail if exists
        companion = abs_path.with_suffix(".jpg")
        if companion.exists():
            companion.unlink()
        return {"status": "deleted", "path": rel_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {e}")

@app.post("/api/cleanup")
async def manual_cleanup():
    """Manually trigger retention cleanup."""
    res = await asyncio.to_thread(run_retention_cleanup, RECORDINGS_PATH, RETENTION_DAYS)
    return res
