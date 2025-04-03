import asyncio
import json
import logging
from websockets.server import serve
from datetime import datetime

# Global variables for connected clients and command results
browser_clients = set()
command_results = {}

logger = logging.getLogger("mcp_server")

async def handle_browser_client(websocket):
    """Handle a connection from the Chrome extension."""
    client_id = f"browser_{len(browser_clients) + 1}"
    browser_clients.add(websocket)
    logger.info(f"New browser client connected: {client_id}. Total browsers: {len(browser_clients)}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Received message from {client_id}: {data}")
                
                # Handle hello message
                if data.get("type") == "hello":
                    logger.info(f"Browser {client_id} capabilities: {data.get('capabilities', [])}")
                    continue
                
                # Store command results
                if "id" in data and ("result" in data or "error" in data):
                    command_id = data["id"]
                    command_results[command_id] = data
                    logger.info(f"Stored result for command {command_id}")
                    continue
                
                # Process any other messages
                logger.info(f"Unhandled message: {data}")
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse message as JSON: {message[:100]}...")
    
    except Exception as e:
        logger.error(f"Error handling client {client_id}: {e}")
    
    finally:
        browser_clients.remove(websocket)
        logger.info(f"Browser {client_id} disconnected. Total browsers: {len(browser_clients)}")

async def send_to_browser(command):
    """Send a command to all connected browser clients."""
    if not browser_clients:
        logger.warning("No browser clients connected. Command not sent.")
        return False
    
    command_json = json.dumps(command)
    await asyncio.gather(
        *[client.send(command_json) for client in browser_clients]
    )
    logger.info(f"Sent command to {len(browser_clients)} browsers: {command}")
    return True

async def start_websocket_server():
    """Start the WebSocket server for browser connections."""
    websocket_port = 8090
    logger.info(f"Starting WebSocket server on port {websocket_port}...")
    async with serve(handle_browser_client, "0.0.0.0", websocket_port):
        # Keep the server running indefinitely
        await asyncio.Future()