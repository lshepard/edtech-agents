from fastapi import APIRouter, HTTPException, status, Request, Query
from pydantic import BaseModel
import asyncio
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List

from app.websocket.server import send_to_browser, browser_clients, command_results
from app.models.schema import NavigateRequest, CommandResponse, ServerStatus, ClientInfo
from app.llm.planner import generate_activity_plan

router = APIRouter()
logger = logging.getLogger("mcp_server")

# Define request model for the planning endpoint
class PlanRequest(BaseModel):
    gradeLevel: str
    workingOn: str

# Define response model for the planning endpoint with structured data
class ActivityRecommendation(BaseModel):
    title: str
    description: str
    rationale: str
    link: Optional[str] = ""

class PlanResponse(BaseModel):
    recommendation: ActivityRecommendation

@router.get("/clients", response_model=List[ClientInfo], summary="Get connected clients")
async def get_clients():
    """API endpoint to get the list of connected browser clients."""
    clients = [
        ClientInfo(id=info["id"], name=info["name"])
        for info in browser_clients.values()
    ]
    return clients

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
async def navigate(
    request: NavigateRequest, 
    target_client: Optional[str] = Query(None, description="Target client ID or name. If not provided, sends to all clients.")
):
    """API endpoint to navigate to a URL."""
    command_id = f"nav_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    command = {
        "id": command_id,
        "action": "navigate",
        "params": {"url": request.url}
    }
    
    success = await send_to_browser(command, target_client)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No browsers connected or target client not found"
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
async def screenshot(
    target_client: Optional[str] = Query(None, description="Target client ID or name. If not provided, sends to all clients.")
):
    """API endpoint to take a screenshot."""
    command_id = f"ss_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    command = {
        "id": command_id,
        "action": "screenshot"
    }
    
    success = await send_to_browser(command, target_client)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No browsers connected or target client not found"
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
async def get_content(
    target_client: Optional[str] = Query(None, description="Target client ID or name. If not provided, sends to all clients.")
):
    """API endpoint to get page content."""
    command_id = f"content_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    command = {
        "id": command_id,
        "action": "getContent"
    }
    
    success = await send_to_browser(command, target_client)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No browsers connected or target client not found"
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
    connected_clients = [
        ClientInfo(id=info["id"], name=info["name"])
        for info in browser_clients.values()
    ]
    
    return {
        "status": "running",
        "browser_clients": len(browser_clients),
        "connected_clients": connected_clients,
        "pending_commands": len(command_results)
    }

@router.post("/plan", response_model=PlanResponse, summary="Plan student activity")
async def plan_activity(request: PlanRequest):
    """API endpoint to plan an activity using LLM and context."""
    logger.info(f"Received plan request: Grade={request.gradeLevel}, WorkingOn='{request.workingOn}'")

    # Call the planning function from the llm module
    try:
        recommendation_data = await generate_activity_plan(
            grade_level=request.gradeLevel,
            working_on=request.workingOn,
        )
        
        # Create the structured response
        recommendation = ActivityRecommendation(
            title=recommendation_data["title"],
            description=recommendation_data["description"],
            rationale=recommendation_data["rationale"],
            link=recommendation_data.get("link", "")
        )
        
        return PlanResponse(recommendation=recommendation)
    except Exception as e:
        # If generate_activity_plan raises an HTTPException, re-raise it.
        # Otherwise, wrap other exceptions.
        if isinstance(e, HTTPException):
            raise e
        logger.error(f"Error during planning: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating activity plan: {e}"
        )

@router.post("/launch-activity", response_model=CommandResponse, summary="Launch activity")
async def launch_activity(
    request: NavigateRequest,
    target_client: Optional[str] = Query(None, description="Target client ID or name. If not provided, sends to all clients.")
):
    """API endpoint to launch an activity by navigating to its URL."""
    command_id = f"launch_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    command = {
        "id": command_id,
        "action": "navigate",
        "params": {"url": request.url}
    }
    
    success = await send_to_browser(command, target_client)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, 
            detail="No browsers connected or target client not found"
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