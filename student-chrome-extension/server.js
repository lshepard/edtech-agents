// A simple WebSocket server implementation
const statusElement = document.getElementById('status');
const PORT = 8080;
let wsServer;

// Start the WebSocket server
function startWebSocketServer() {
  try {
    // Create a WebSocket server
    wsServer = new WebSocket.Server({ port: PORT });
    
    statusElement.textContent = `WebSocket server running on port ${PORT}`;
    
    // Inform the background script that the server is running
    chrome.runtime.sendMessage({
      type: 'serverStarted',
      port: PORT
    });
    
    // Handle new client connections
    wsServer.on('connection', (socket) => {
      statusElement.textContent = `Client connected! Total clients: ${wsServer.clients.size}`;
      
      // Handle messages from clients
      socket.on('message', async (message) => {
        try {
          const data = JSON.parse(message);
          
          // Forward the command to the background script
          chrome.runtime.sendMessage({
            type: 'command',
            command: data,
            id: data.id || Math.random().toString(36).substring(2, 9)
          });
        } catch (error) {
          console.error('Error parsing message:', error);
          socket.send(JSON.stringify({
            success: false,
            error: 'Invalid message format'
          }));
        }
      });
      
      // Handle disconnections
      socket.on('close', () => {
        statusElement.textContent = `Client disconnected. Total clients: ${wsServer.clients.size}`;
      });
    });
  } catch (error) {
    statusElement.textContent = `Failed to start WebSocket server: ${error.message}`;
    console.error('Server error:', error);
  }
}

// Listen for command results from the background script
chrome.runtime.onMessage.addListener((message) => {
  if (message.type === 'commandResult') {
    // Send the result to all connected clients
    if (wsServer && wsServer.clients) {
      wsServer.clients.forEach((client) => {
        if (client.readyState === WebSocket.OPEN) {
          client.send(JSON.stringify({
            id: message.id,
            result: message.result
          }));
        }
      });
    }
  }
  return true;
});

// Start the server when the page loads
window.addEventListener('load', startWebSocketServer);