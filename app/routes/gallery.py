from fastapi import APIRouter, Request, HTTPException, Depends
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.templating import Jinja2Templates
import os
from pathlib import Path
from app.websocket.server import get_screenshot_history
import asyncio

router = APIRouter(prefix="/gallery", tags=["gallery"])

# Set up templates
templates_dir = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(templates_dir))

# Screenshot directory
SCREENSHOTS_DIR = Path(__file__).parent.parent.parent / "screenshots"

@router.get("/", response_class=HTMLResponse)
async def screenshot_gallery(request: Request, client_id: str = None):
    """Display a gallery of screenshots for a student's browsing session."""
    # Get screenshot history
    history = await get_screenshot_history(client_id)
    
    # Get list of available clients
    clients = list(history.keys())
    
    # If client_id is not specified and there are clients, use the first one
    if not client_id and clients:
        client_id = clients[0]
    
    # Get screenshots for the selected client
    screenshots = history.get(client_id, []) if client_id else []
    
    # Sort screenshots by timestamp (newest first)
    screenshots.sort(key=lambda x: x["timestamp"], reverse=True)
    
    return templates.TemplateResponse(
        "gallery.html",
        {
            "request": request,
            "clients": clients,
            "selected_client": client_id,
            "screenshots": screenshots
        }
    )

@router.get("/screenshot/{filename}")
async def get_screenshot(filename: str):
    """Serve a screenshot image file."""
    file_path = SCREENSHOTS_DIR / filename
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Screenshot not found")
    
    return FileResponse(file_path) 