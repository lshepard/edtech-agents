// Save settings
document.getElementById('saveBtn').addEventListener('click', function() {
    const serverUrl = document.getElementById('serverUrl').value.trim();
    const autoConnect = document.getElementById('autoConnect').checked;
    const statusElement = document.getElementById('status');
    
    // Validate the WebSocket URL
    if (!serverUrl) {
      showStatus('Please enter a valid WebSocket URL', 'error');
      return;
    }
    
    if (!serverUrl.startsWith('ws://') && !serverUrl.startsWith('wss://')) {
      showStatus('WebSocket URL must start with ws:// or wss://', 'error');
      return;
    }
    
    // Save the settings
    chrome.storage.local.set({
      mcpServerUrl: serverUrl,
      autoConnect: autoConnect
    }, function() {
      if (chrome.runtime.lastError) {
        showStatus('Error saving settings: ' + chrome.runtime.lastError.message, 'error');
        return;
      }
      
      showStatus('Settings saved successfully!', 'success');
      
      // Notify the background script that settings have changed
      chrome.runtime.sendMessage({ type: 'settingsChanged' });
    });
  });
  
  // Load saved settings
  function loadSettings() {
    chrome.storage.local.get(['mcpServerUrl', 'autoConnect'], function(result) {
      if (result.mcpServerUrl) {
        document.getElementById('serverUrl').value = result.mcpServerUrl;
      }
      
      document.getElementById('autoConnect').checked = !!result.autoConnect;
    });
  }
  
  // Show status message
  function showStatus(message, type) {
    const statusElement = document.getElementById('status');
    statusElement.textContent = message;
    statusElement.className = 'status ' + type;
    statusElement.style.display = 'block';
    
    // Hide the status message after 3 seconds
    setTimeout(function() {
      statusElement.style.display = 'none';
    }, 3000);
  }
  
  // Load settings when the page opens
  document.addEventListener('DOMContentLoaded', loadSettings);