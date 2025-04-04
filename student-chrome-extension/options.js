// Save settings
document.getElementById('saveBtn').addEventListener('click', function() {
    const serverUrl = document.getElementById('serverUrl').value.trim();
    const userName = document.getElementById('userName').value.trim();
    const statusElement = document.getElementById('status');
    
    // Get activity tracking settings
    const enableTracking = document.getElementById('enableTracking').checked;
    
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
      socketServerUrl: serverUrl,
      userName: userName,
      
      // Activity tracking settings
      enableTracking: enableTracking
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
    chrome.storage.local.get([
      'socketServerUrl', 
      'autoConnect', 
      'userName', 
      'enableTracking'
    ], function(result) {
      if (result.socketServerUrl) {
        document.getElementById('serverUrl').value = result.socketServerUrl;
      }
      
      if (result.userName) {
        document.getElementById('userName').value = result.userName;
      }
      
      document.getElementById('autoConnect').checked = !!result.autoConnect;
      
      // Load activity tracking settings
      document.getElementById('enableTracking').checked = 
        result.enableTracking === undefined ? true : !!result.enableTracking;
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
  
  // Toggle the individual tracking options based on master toggle
  document.getElementById('enableTracking').addEventListener('change', function(event) {
    const trackingEnabled = event.target.checked;
  });
  
  // Load settings when the page opens
  document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    
    // Initialize tracking options state based on master toggle
    const trackingEnabled = document.getElementById('enableTracking').checked;
  });