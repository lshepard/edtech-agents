// WebSocket connection
let socket = null;
let connectionAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
let reconnectTimer = null;
// Buffer for activity data in case the socket is temporarily disconnected
let activityBuffer = [];
const MAX_BUFFER_SIZE = 100; // Limit the buffer size to prevent memory issues

// Connect to the MCP server
function connectToMcpServer() {
  // Clear any existing reconnect timer
  if (reconnectTimer) {
    clearTimeout(reconnectTimer);
    reconnectTimer = null;
  }
  
  // Get the server URL from settings
  chrome.storage.local.get(['mcpServerUrl', 'userName'], function(result) {
    const serverUrl = result.mcpServerUrl;
    const userName = result.userName || 'Anonymous';
    
    if (!serverUrl) {
      console.log('No MCP server URL configured. Please set one in the extension options.');
      return;
    }
    
    // Close existing connection if any
    if (socket) {
      socket.close();
      socket = null;
    }
    
    // Connect to the MCP server
    try {
      console.log('Connecting to MCP server at ' + serverUrl);
      socket = new WebSocket(serverUrl);
      
      // Add additional debugging
      console.log('WebSocket object created, readyState:', socket.readyState);
      // 0: connecting, 1: open, 2: closing, 3: closed
      
      socket.onopen = function() {
        console.log('Connected to MCP server!');
        connectionAttempts = 0;
        
        // Send a hello message to the server
        const helloMessage = {
          type: 'hello',
          client: 'remote-browser-controller',
          name: userName,
          capabilities: ['navigate', 'screenshot', 'getContent', 'userActivity']
        };
        console.log('Sending hello message:', helloMessage);
        socket.send(JSON.stringify(helloMessage));
        
        // Send any buffered activity data
        if (activityBuffer.length > 0) {
          console.log(`Sending ${activityBuffer.length} buffered activity events`);
          activityBuffer.forEach(activity => {
            sendActivityToServer(activity, false); // Don't buffer again if sending fails
          });
          activityBuffer = []; // Clear buffer after sending
        }
      };
      
      socket.onmessage = function(event) {
        try {
          const message = JSON.parse(event.data);
          handleCommand(message)
            .then(result => {
              // Send the result back to the MCP server
              if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                  id: message.id || 'unknown',
                  result: result
                }));
              }
            })
            .catch(error => {
              console.error('Error handling command:', error);
              
              // Send error back to the MCP server
              if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                  id: message.id || 'unknown',
                  error: error.message || 'Unknown error'
                }));
              }
            });
        } catch (error) {
          console.error('Error parsing message:', error);
        }
      };
      
      socket.onclose = function() {
        console.log('Disconnected from MCP server');
        
        // Try to reconnect after a delay, with exponential backoff
        connectionAttempts++;
        if (connectionAttempts <= MAX_RECONNECT_ATTEMPTS) {
          const delay = Math.min(30000, Math.pow(2, connectionAttempts) * 1000);
          console.log(`Reconnecting in ${delay/1000} seconds (attempt ${connectionAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
          
          reconnectTimer = setTimeout(connectToMcpServer, delay);
        } else {
          console.log('Max reconnection attempts reached. Please reconnect manually.');
        }
      };
      
      socket.onerror = function(error) {
        console.error('Socket error details:', JSON.stringify(error));
      };
    } catch (error) {
      console.error('Error connecting to MCP server:', error);
    }
  });
}

// Handle remote commands
async function handleCommand(command) {
  console.log('Received command:', command);
  
  if (!command.action) {
    throw new Error('No action specified in command');
  }
  
  switch (command.action) {
    case 'navigate':
      return await navigateToUrl(command.params?.url);
    
    case 'screenshot':
      return await takeScreenshot();
      
    case 'getContent':
      return await getPageContent();

    case 'getUserActivity':
      return await getUserActivityLog(command.params?.limit || 20);
      
    default:
      throw new Error('Unknown command: ' + command.action);
  }
}

// New command to retrieve recent user activity
async function getUserActivityLog(limit) {
  // This would return the most recent activity events from storage
  return new Promise((resolve) => {
    chrome.storage.local.get(['userActivityLog'], function(result) {
      const activityLog = result.userActivityLog || [];
      resolve({
        success: true, 
        activities: activityLog.slice(-limit) // Return the most recent 'limit' events
      });
    });
  });
}

// Send user activity to the server
function sendActivityToServer(activity, bufferIfDisconnected = true) {
  // Check if we're connected to the server
  if (socket && socket.readyState === WebSocket.OPEN) {
    // Format the message for the server
    const message = {
      type: 'userActivity',
      activity: activity
    };
    
    try {
      socket.send(JSON.stringify(message));
      console.log('Sent activity to server:', activity.activity);
      return true;
    } catch (error) {
      console.error('Error sending activity to server:', error);
      if (bufferIfDisconnected) {
        bufferActivity(activity);
      }
      return false;
    }
  } else {
    if (bufferIfDisconnected) {
      bufferActivity(activity);
    }
    return false;
  }
}

// Buffer activity data if socket is not connected
function bufferActivity(activity) {
  // Add to buffer if not already full
  if (activityBuffer.length < MAX_BUFFER_SIZE) {
    activityBuffer.push(activity);
    console.log('Buffered activity:', activity.activity);
  } else {
    // Remove oldest item if buffer is full
    activityBuffer.shift();
    activityBuffer.push(activity);
    console.log('Buffer full, replaced oldest activity with:', activity.activity);
  }
  
  // Also store in local storage for history
  chrome.storage.local.get(['userActivityLog'], function(result) {
    let activityLog = result.userActivityLog || [];
    
    // Limit the size of the activity log
    if (activityLog.length >= 200) {
      activityLog = activityLog.slice(-150); // Keep the most recent 150 events
    }
    
    activityLog.push(activity);
    chrome.storage.local.set({userActivityLog: activityLog});
  });
}

// Command implementations
async function navigateToUrl(url) {
  if (!url) {
    throw new Error('No URL specified for navigate command');
  }
  
  return new Promise((resolve, reject) => {
    // Always create a new tab for navigation commands
    chrome.tabs.create({url: url}, function(tab) {
      if (chrome.runtime.lastError) {
        reject(chrome.runtime.lastError.message);
        return;
      }
      resolve({success: true, tab: {id: tab.id, url: tab.url}});
    });
  });
}

async function takeScreenshot() {
  return new Promise((resolve, reject) => {
    chrome.tabs.captureVisibleTab(null, {format: 'png'}, function(dataUrl) {
      if (chrome.runtime.lastError) {
        reject(chrome.runtime.lastError.message);
        return;
      }
      
      // Extract base64 image data
      const base64Data = dataUrl.split(',')[1];
      resolve({success: true, screenshot: base64Data});
    });
  });
}

async function getPageContent() {
  return new Promise((resolve, reject) => {
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (tabs.length === 0) {
        reject('No active tab');
        return;
      }
      
      chrome.scripting.executeScript({
        target: {tabId: tabs[0].id},
        function: () => document.documentElement.outerHTML
      }, (results) => {
        if (chrome.runtime.lastError) {
          reject(chrome.runtime.lastError.message);
          return;
        }
        
        if (!results || results.length === 0) {
          reject('No result from script execution');
          return;
        }
        
        resolve({success: true, content: results[0].result});
      });
    });
  });
}

// Listen for messages from the popup or options page
chrome.runtime.onMessage.addListener(function(message, sender, sendResponse) {
  if (message.type === 'connect') {
    connectToMcpServer();
    sendResponse({success: true});
  } else if (message.type === 'disconnect') {
    if (socket) {
      socket.close();
      socket = null;
    }
    sendResponse({success: true});
  } else if (message.type === 'getStatus') {
    sendResponse({
      connected: socket !== null && socket.readyState === WebSocket.OPEN
    });
  } else if (message.type === 'settingsChanged') {
    // Reconnect if settings have changed
    console.log("Settings changed, resetting connection attempts to 0 and reconnecting");
    connectionAttempts = 0
    connectToMcpServer();
    sendResponse({success: true});
  } else if (message.type === 'userActivity') {
    // Process user activity from content script
    console.log('Received user activity:', message.activity);
    
    // Add tab information to the activity data
    if (sender.tab) {
      message.data = message.data || {};
      message.data.tabId = sender.tab.id;
      message.data.tabUrl = sender.tab.url;
      message.data.tabTitle = sender.tab.title;
    }
    
    // Forward to server
    sendActivityToServer({
      type: message.activity,
      data: message.data
    });
    
    sendResponse({success: true});
  }
  
  return true; // Keep the message channel open for async responses
});

// Connect on startup if auto-connect is enabled
chrome.runtime.onStartup.addListener(function() {
  chrome.storage.local.get(['autoConnect'], function(result) {
    if (result.autoConnect) {
      connectToMcpServer();
    }
  });
});

// Try to connect when the extension is installed/updated
chrome.runtime.onInstalled.addListener(function() {
  // Set default settings if not already set
  chrome.storage.local.get(['mcpServerUrl', 'autoConnect', 'userName'], function(result) {
    const updates = {};
    
    if (!result.mcpServerUrl) {
      updates.mcpServerUrl = 'wss://socket.learninghelper.org';
    }
    
    if (result.autoConnect === undefined) {
      updates.autoConnect = true;
    }
    
    if (!result.userName) {
      updates.userName = 'Student';
    }
    
    if (Object.keys(updates).length > 0) {
      chrome.storage.local.set(updates);
    }
  });
});