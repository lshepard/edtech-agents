import asyncio
import json
import logging
from websockets.server import serve
from datetime import datetime

# Global variables for connected clients and command results
browser_clients = {}  # Change to dictionary to store client info
command_results = {}

# Global variables to keep track of the server
websocket_server = None
server_task = None

logger = logging.getLogger("mcp_server")

async def handle_browser_client(websocket):
    """Handle a connection from the Chrome extension."""
    client_id = f"browser_{len(browser_clients) + 1}"
    client_name = "Unknown"  # Default name until hello message received
    browser_clients[websocket] = {"id": client_id, "name": client_name}
    logger.info(f"New browser client connected: {client_id}. Total browsers: {len(browser_clients)}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                
                # Handle hello message
                if data.get("type") == "hello":
                    # Update client name if provided in hello message
                    if "name" in data:
                        client_name = data["name"]
                        browser_clients[websocket]["name"] = client_name
                        logger.info(f"Browser {client_id} identified as user: {client_name}")
                    
                    logger.info(f"Browser {client_id} ({client_name}) capabilities: {data.get('capabilities', [])}")
                    continue
                
                # Store command results
                if "id" in data and ("result" in data or "error" in data):
                    command_id = data["id"]
                    command_results[command_id] = data
                    logger.info(f"Stored result for command {command_id} from {client_name} ({client_id})")
                    continue
                
                # Process any other messages
                logger.info(f"Unhandled message from {client_name} ({client_id}): {data}")
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse message as JSON from {client_name} ({client_id}): {message[:100]}...")
    
    except Exception as e:
        logger.error(f"Error handling client {client_name} ({client_id}): {e}")
    
    finally:
        del browser_clients[websocket]
        logger.info(f"Browser {client_name} ({client_id}) disconnected. Total browsers: {len(browser_clients)}")

async def send_to_browser(command, target_client=None):
    """Send a command to browser clients.
    
    Args:
        command: The command to send
        target_client: Optional. Either a username, client_id, or None to send to all (broadcast)
    
    Returns:
        bool: Success status
    """
    if not browser_clients:
        logger.warning("No browser clients connected. Command not sent.")
        return False
    
    command_json = json.dumps(command)
    
    # If no target specified, broadcast to all clients
    if target_client is None:
        await asyncio.gather(
            *[client.send(command_json) for client in browser_clients.keys()]
        )
        client_info = ", ".join([f"{info['name']} ({info['id']})" for info in browser_clients.values()])
        logger.info(f"Broadcast command to {len(browser_clients)} browsers ({client_info}): {command}")
        return True
    
    # Find target client by name or id
    target_websocket = None
    for websocket, info in browser_clients.items():
        if target_client == info['name'] or target_client == info['id']:
            target_websocket = websocket
            break
    
    if target_websocket:
        await target_websocket.send(command_json)
        client_info = f"{browser_clients[target_websocket]['name']} ({browser_clients[target_websocket]['id']})"
        logger.info(f"Sent command to specific browser {client_info}: {command}")
        return True
    else:
        logger.warning(f"Target client '{target_client}' not found. Command not sent.")
        return False

async def start_websocket_server():
    """Start the WebSocket server for browser connections."""
    global websocket_server
    websocket_port = 8090
    
    # If we already have a server running, don't start a new one
    if websocket_server is not None:
        logger.info("WebSocket server already running, not starting a new one")
        return websocket_server
    
    logger.info(f"Starting WebSocket server on port {websocket_port}...")
    
    try:
        # Create the server
        websocket_server = await serve(handle_browser_client, "0.0.0.0", websocket_port)
        logger.info(f"WebSocket server successfully started on port {websocket_port}")
        return websocket_server
    except Exception as e:
        logger.error(f"Failed to start WebSocket server: {e}")
        websocket_server = None
        raise

async def stop_websocket_server():
    """Gracefully stop the WebSocket server."""
    global websocket_server
    
    if websocket_server is not None:
        logger.info("Shutting down WebSocket server...")
        websocket_server.close()
        await websocket_server.wait_closed()
        websocket_server = None
        logger.info("WebSocket server has been shut down")