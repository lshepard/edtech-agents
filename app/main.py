import asyncio
import uvicorn
import logging
import os
from dotenv import load_dotenv

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates

# Load environment variables from .env file BEFORE other imports that might need them
load_dotenv()

from app.api.routes import router as api_router
from app.websocket.server import start_websocket_server
from app.routes.gallery import router as gallery_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

# Create FastAPI app
app = FastAPI(
    title="Remote Browser MCP Server",
    description="MCP Server for controlling remote browsers and planning activities",
    version="1.0.0"
)

# Setup templates directory
templates = Jinja2Templates(directory="app/templates")

# Mount static files directory
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix="/api")

# Include gallery routes
app.include_router(gallery_router)

# Route to serve the main HTML page
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

# Start WebSocket server when FastAPI starts
@app.on_event("startup")
async def startup_event():
    # Start WebSocket server in a background task
    asyncio.create_task(start_websocket_server())
    logger.info("WebSocket server started in background task")

if __name__ == "__main__":
    # Note: load_dotenv() is already called at the top level
    uvicorn.run("app.main:app", host="0.0.0.0", port=3030, reload=True)