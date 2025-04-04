from fastapi import APIRouter, HTTPException, status, Request, Query, Depends, BackgroundTasks
from pydantic import BaseModel
import asyncio
from datetime import datetime
import logging
from typing import Dict, Any, Optional, List

from app.websocket.server import send_to_browser, browser_clients, command_results, get_screenshot_history, start_periodic_screenshots, stop_periodic_screenshots, SCREENSHOT_INTERVAL
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
    all_recommendations: List[ActivityRecommendation] = []
    planning_process: str = ""

class ScreenshotSettings(BaseModel):
    """Settings for periodic screenshots."""
    interval: int  # Interval in seconds
    enabled: bool = True

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
        plan_data = await generate_activity_plan(
            grade_level=request.gradeLevel,
            working_on=request.workingOn,
        )
        
        # Primary recommendation is already in the right format
        primary_rec = plan_data["primary_recommendation"]
        
        # Create the list of all recommendations
        all_recs = []
        for rec in plan_data.get("recommendations", []):
            all_recs.append(ActivityRecommendation(
                title=rec["title"],
                description=rec["description"],
                rationale=rec["rationale"],
                link=rec.get("link", "")
            ))
            
        # Generate a planning process summary based on the primary recommendation
        planning_process = f"An activity plan was created for a Grade {request.gradeLevel} student working on {request.workingOn}. "
        
        # Add explanation of the tool's functionality
        planning_process += "The AI teaching assistant analyzed the student's grade level and learning needs, "
        
        # Mention if it used local resources or web search
        if "local resources" in primary_rec["rationale"].lower():
            planning_process += "then identified relevant pre-vetted local resources that match these requirements. "
        elif "web search" in primary_rec["rationale"].lower():
            planning_process += "searched for high-quality educational resources on the web since no local resources matched exactly. "
        else:
            planning_process += "then identified appropriate educational resources for this student. "
            
        planning_process += "The AI carefully considered grade-level appropriateness, alignment with learning objectives, and engagement factors. "
        planning_process += "The recommended activity was selected because it best addresses the specific skills the student is working on."
        
        # Create the primary recommendation
        primary = ActivityRecommendation(
            title=primary_rec["title"],
            description=primary_rec["description"],
            rationale=primary_rec["rationale"],
            link=primary_rec.get("link", "")
        )
        
        return PlanResponse(
            recommendation=primary,
            all_recommendations=all_recs,
            planning_process=planning_process
        )
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

@router.post("/screenshots/settings", response_model=Dict[str, Any])
async def update_screenshot_settings(settings: ScreenshotSettings):
    """Update periodic screenshot settings."""
    if settings.interval < 5:
        raise HTTPException(status_code=400, detail="Interval must be at least 5 seconds")
    
    if settings.enabled:
        # Start or restart periodic screenshots with the new interval
        await start_periodic_screenshots(settings.interval)
        return {
            "status": "success",
            "message": f"Periodic screenshots enabled with interval of {settings.interval} seconds",
            "settings": settings.dict()
        }
    else:
        # Stop periodic screenshots
        stopped = await stop_periodic_screenshots()
        return {
            "status": "success",
            "message": "Periodic screenshots disabled" if stopped else "Periodic screenshots were already disabled",
            "settings": settings.dict()
        }

@router.get("/screenshots/settings")
async def get_screenshot_settings():
    """Get current screenshot settings."""
    from app.websocket.server import periodic_screenshot_task, SCREENSHOT_INTERVAL
    
    return {
        "enabled": periodic_screenshot_task is not None,
        "interval": SCREENSHOT_INTERVAL
    }