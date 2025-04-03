from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
import asyncio
import json
from datetime import datetime
import logging

from app.websocket.server import send_to_browser, browser_clients, command_results
from app.models.schema import NavigateRequest, CommandResponse, ServerStatus

router = APIRouter()
logger = logging.getLogger("mcp_server")

@router.get("/discovery", summary="Discover server capabilities")
async def get_discovery():
    """API endpoint for capability discovery."""
    return {
        "name": "Remote Browser Controller",
        "version": "1.0",
        "capabilities": [
            {
                "name": "navigate",
                "description": "Navigate to a URL",
                "endpoint": "/api/navigate",
                "method": "POST",
                "parameters": {
                    "url": {
                        "type": "string",
                        "description": "URL to navigate to",
                        "required": True
                    }
                }
            },
            {
                "name": "screenshot",
                "description": "Take a screenshot of the current page",
                "endpoint": "/api/screenshot",
                "method": "POST"
            },
            {
                "name": "getContent",
                "description": "Get the HTML content of the current page",
                "endpoint": "/api/content",
                "method": "POST"
            }
        ]
    }

@router.post("/navigate", response_model=CommandResponse, summary="Navigate to URL")
async def navigate(request: NavigateRequest):
    """API endpoint to navigate to a URL."""
    command_id = f"nav_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    command = {
        "id": command_id,
        "action": "navigate",
        "params": {"url": request.url}
    }
    
    success = await send_to_browser(command)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No browsers connected"
        )
    
    # Wait for the result (with timeout)
    for _ in range(30):  # 3 second timeout
        if command_id in command_results:
            return command_results.pop(command_id)
        await asyncio.sleep(0.1)
    
    raise HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT, 
        detail="Command timed out"
    )

@router.post("/screenshot", response_model=CommandResponse, summary="Take screenshot")
async def screenshot():
    """API endpoint to take a screenshot."""
    command_id = f"ss_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    command = {
        "id": command_id,
        "action": "screenshot"
    }
    
    success = await send_to_browser(command)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No browsers connected"
        )
    
    # Wait for the result (with timeout)
    for _ in range(50):  # 5 second timeout
        if command_id in command_results:
            return command_results.pop(command_id)
        await asyncio.sleep(0.1)
    
    raise HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT, 
        detail="Command timed out"
    )

@router.post("/content", response_model=CommandResponse, summary="Get page content")
async def get_content():
    """API endpoint to get page content."""
    command_id = f"content_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    command = {
        "id": command_id,
        "action": "getContent"
    }
    
    success = await send_to_browser(command)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No browsers connected"
        )
    
    # Wait for the result (with timeout)
    for _ in range(50):  # 5 second timeout
        if command_id in command_results:
            return command_results.pop(command_id)
        await asyncio.sleep(0.1)
    
    raise HTTPException(
        status_code=status.HTTP_504_GATEWAY_TIMEOUT, 
        detail="Command timed out"
    )

@router.get("/status", response_model=ServerStatus, summary="Check server status")
async def get_status():
    """API endpoint to check server status."""
    return {
        "status": "running",
        "browser_clients": len(browser_clients),
        "pending_commands": len(command_results)
    }