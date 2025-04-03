import asyncio
import json
import base64
import logging
from websockets.server import serve
from datetime import datetime
import aioconsole

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mcp_server.log'),
        logging.StreamHandler()  # Keep console output for important messages
    ]
)
logger = logging.getLogger("mcp_server")

# Connected clients
clients = set()

async def handle_client(websocket):
    """Handle a connection from the Chrome extension."""
    client_id = f"client_{len(clients) + 1}"
    clients.add(websocket)
    logger.info(f"New client connected: {client_id}. Total clients: {len(clients)}")
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Received message from {client_id}: {data}")
                
                # Handle hello message
                if data.get("type") == "hello":
                    logger.info(f"Client {client_id} capabilities: {data.get('capabilities', [])}")
                    continue
                
                # Handle command results
                if "result" in data:
                    logger.info(f"Received result for command {data.get('id')}")
                    
                    # If the result contains a screenshot, save it to a file
                    if "screenshot" in data.get("result", {}):
                        filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
                        with open(filename, "wb") as f:
                            img_data = base64.b64decode(data["result"]["screenshot"])
                            f.write(img_data)
                        logger.info(f"Saved screenshot to {filename}")
                    
                    continue
                
                # Process any other messages
                logger.info(f"Unhandled message: {data}")
                
            except json.JSONDecodeError:
                logger.error(f"Failed to parse message as JSON: {message[:100]}...")
    
    except Exception as e:
        logger.error(f"Error handling client {client_id}: {e}")
    
    finally:
        clients.remove(websocket)
        logger.info(f"Client {client_id} disconnected. Total clients: {len(clients)}")

async def send_command(command):
    """Send a command to all connected clients."""
    if not clients:
        logger.warning("No clients connected. Command not sent.")
        return False
    
    command_json = json.dumps(command)
    await asyncio.gather(
        *[client.send(command_json) for client in clients]
    )
    logger.info(f"Sent command to {len(clients)} clients: {command}")
    return True

async def command_interface():
    """A simple command-line interface for sending commands."""
    while True:
        print("\nAvailable commands:")
        print("1. Navigate to URL")
        print("2. Take screenshot")
        print("3. Get page content")
        print("q. Quit")
        
        choice = await aioconsole.ainput("Enter command (1-3, q): ")
        choice = choice.strip()
        
        if choice == "q":
            print("Exiting command interface...")
            break
        
        command = {
            "id": f"cmd_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        }
        
        if choice == "1":
            url = await aioconsole.ainput("Enter URL to navigate to: ")
            url = url.strip()
            if not (url.startswith("http://") or url.startswith("https://")):
                url = "https://" + url
            command["action"] = "navigate"
            command["params"] = {"url": url}
            
        elif choice == "2":
            command["action"] = "screenshot"
            
        elif choice == "3":
            command["action"] = "getContent"
            
        else:
            print("Invalid choice.")
            continue
        
        success = await send_command(command)
        if success:
            print(f"Command sent: {command['action']}")

async def main():
    # Start the server
    host = "0.0.0.0"  # Listen on all network interfaces
    port = 8090
    
    logger.info(f"Starting MCP server on {host}:{port}...")
    async with serve(handle_client, host, port):
        # Start the command interface in the background
        command_task = asyncio.create_task(command_interface())
        
        try:
            # Wait for the command interface to complete
            await command_task
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            command_task.cancel()
            try:
                await command_task
            except asyncio.CancelledError:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server shutting down...")