from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import uvicorn
import logging

from app.api.routes import router as api_router
from app.websocket.server import start_websocket_server

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_server")

# Create FastAPI app
app = FastAPI(
    title="Remote Browser MCP Server",
    description="MCP Server for controlling remote browsers",
    version="1.0.0"
)

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

# Mount static files for the test interface
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")

# Start WebSocket server when FastAPI starts
@app.on_event("startup")
async def startup_event():
    # Start WebSocket server in a background task
    asyncio.create_task(start_websocket_server())
    logger.info("WebSocket server started in background task")

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=3030, reload=True)