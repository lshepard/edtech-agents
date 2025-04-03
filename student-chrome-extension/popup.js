// Handle navigation
document.getElementById('navigateBtn').addEventListener('click', function() {
  const url = document.getElementById('urlInput').value;
  
  // Basic URL validation
  if (!url.startsWith('http://') && !url.startsWith('https://')) {
    alert('Please enter a URL starting with http:// or https://');
    return;
  }
  
  // Navigate to the URL in the current tab
  chrome.tabs.update({ url: url });
});

// Handle connection button
document.getElementById('connectBtn').addEventListener('click', function() {
  chrome.runtime.sendMessage({ type: 'connect' }, function(response) {
    updateConnectionStatus();
  });
});

// Handle disconnection button
document.getElementById('disconnectBtn').addEventListener('click', function() {
  chrome.runtime.sendMessage({ type: 'disconnect' }, function(response) {
    updateConnectionStatus();
  });
});

// Handle settings button
document.getElementById('settingsBtn').addEventListener('click', function() {
  chrome.runtime.openOptionsPage();
});

// Update connection status
function updateConnectionStatus() {
  const statusElement = document.getElementById('connectionStatus');
  
  chrome.runtime.sendMessage({ type: 'getStatus' }, function(response) {
    if (response.connected) {
      statusElement.textContent = 'Connected to MCP Server';
      statusElement.className = 'status connected';
    } else {
      statusElement.textContent = 'Disconnected from MCP Server';
      statusElement.className = 'status disconnected';
    }
  });
}

// Update status when popup opens
document.addEventListener('DOMContentLoaded', updateConnectionStatus);