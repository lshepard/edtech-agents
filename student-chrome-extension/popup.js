// Handle navigation
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
      statusElement.textContent = 'Connected to Socket Server';
      statusElement.className = 'status connected';
    } else {
      statusElement.textContent = 'Disconnected from Socket Server';
      statusElement.className = 'status disconnected';
    }
  });
}

// Update status when popup opens
document.addEventListener('DOMContentLoaded', updateConnectionStatus);