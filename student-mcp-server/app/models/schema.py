from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional, List, Union

class NavigateRequest(BaseModel):
    url: str
    
    class Config:
        schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }

class CommandResult(BaseModel):
    success: bool
    screenshot: Optional[str] = None
    content: Optional[str] = None
    tab: Optional[Dict[str, Any]] = None

class CommandResponse(BaseModel):
    id: str
    result: Optional[CommandResult] = None
    error: Optional[str] = None

class ServerStatus(BaseModel):
    status: str
    browser_clients: int
    pending_commands: int