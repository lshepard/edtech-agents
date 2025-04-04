import asyncio
import json
import logging
from websockets.server import serve
from datetime import datetime
import uuid
import os
import base64

# Global variables for connected clients and command results
browser_clients = {}  # Change to dictionary to store client info
command_results = {}
screenshot_history = {}  # Store screenshot history by client

# Global variables to keep track of the server
websocket_server = None
server_task = None

# Configure logging
logger = logging.getLogger("mcp_server")

# Create screenshots directory if it doesn't exist
SCREENSHOTS_DIR = os.path.join(os.path.dirname(__file__), '../../screenshots')
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def handle_browser_client(websocket):
    """Handle a connection from the Chrome extension."""
    client_id = f"browser_{len(browser_clients) + 1}"
    client_name = "Unknown"  # Default name until hello message received
    browser_clients[websocket] = {"id": client_id, "name": client_name}
    logger.info(f"New browser client connected: {client_id}. Total browsers: {len(browser_clients)}")
    
    # Initialize screenshot history for this client
    screenshot_history[client_id] = []
    
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
                    
                    # If this is a screenshot result, save it
                    if "result" in data and "screenshot" in data["result"]:
                        await save_screenshot(client_id, client_name, data["result"]["screenshot"], command_id)
                    
                    logger.info(f"Stored result for command {command_id} from {client_name} ({client_id})")
                    continue
                
                # Handle user activity
                if data.get("type") == "userActivity":
                    activity = data.get("activity", {})
                    activity_type = activity.get("type")
                    
                    logger.info(f"Received user activity from {client_name} ({client_id}): {activity_type}")
                    
                    # Trigger screenshot capture for significant events
                    if activity_type in ["pageLoad", "pageNavigation", "click", "formSubmission"]:
                        await capture_screenshot_for_activity(websocket, client_id, client_name, activity)
                    
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

async def capture_screenshot_for_activity(websocket, client_id, client_name, activity):
    """Capture a screenshot when significant user activity occurs."""
    # Generate a unique command ID
    command_id = f"screenshot_{uuid.uuid4()}"
    
    # Create screenshot command
    command = {
        "id": command_id,
        "action": "screenshot"
    }
    
    logger.info(f"Requesting screenshot from {client_name} ({client_id}) for activity: {activity.get('type')}")
    
    try:
        # Send screenshot command to the browser
        await websocket.send(json.dumps(command))
        
        # Wait for the result (in a real implementation, you might want to use asyncio.wait_for with a timeout)
        # The result will be handled in the message handler when it arrives
    except Exception as e:
        logger.error(f"Error requesting screenshot from {client_name} ({client_id}): {e}")

async def save_screenshot(client_id, client_name, screenshot_base64, command_id):
    """Save a screenshot to disk and record it in history."""
    try:
        # Generate a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{client_id}_{timestamp}_{command_id[:8]}.png"
        filepath = os.path.join(SCREENSHOTS_DIR, filename)
        
        # Save the image to disk
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(screenshot_base64))
        
        # Add to screenshot history
        screenshot_info = {
            "filename": filename,
            "filepath": filepath,
            "timestamp": timestamp,
            "datetime": datetime.now().isoformat(),
            "client_id": client_id,
            "client_name": client_name
        }
        
        screenshot_history[client_id].append(screenshot_info)
        
        # Limit history size (keep last 50 screenshots per client)
        if len(screenshot_history[client_id]) > 50:
            screenshot_history[client_id] = screenshot_history[client_id][-50:]
        
        logger.info(f"Saved screenshot for {client_name} ({client_id}): {filepath}")
        
        return filepath
    except Exception as e:
        logger.error(f"Error saving screenshot: {e}")
        return None

async def get_screenshot_history(client_id=None):
    """Get screenshot history for a specific client or all clients."""
    if client_id and client_id in screenshot_history:
        return {client_id: screenshot_history[client_id]}
    return screenshot_history

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