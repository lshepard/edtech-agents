// Save settings
document.getElementById('saveBtn').addEventListener('click', function() {
    const serverUrl = document.getElementById('serverUrl').value.trim();
    const autoConnect = document.getElementById('autoConnect').checked;
    const userName = document.getElementById('userName').value.trim();
    const statusElement = document.getElementById('status');
    
    // Get activity tracking settings
    const enableTracking = document.getElementById('enableTracking').checked;
    const trackPageNavigation = document.getElementById('trackPageNavigation').checked;
    const trackClicks = document.getElementById('trackClicks').checked;
    const trackFormInput = document.getElementById('trackFormInput').checked;
    const trackScrolling = document.getElementById('trackScrolling').checked;
    const trackTimeSpent = document.getElementById('trackTimeSpent').checked;
    
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
      autoConnect: autoConnect,
      userName: userName,
      
      // Activity tracking settings
      enableTracking: enableTracking,
      trackingSettings: {
        pageNavigation: trackPageNavigation,
        clicks: trackClicks,
        formInput: trackFormInput,
        scrolling: trackScrolling,
        timeSpent: trackTimeSpent
      }
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
      'mcpServerUrl', 
      'autoConnect', 
      'userName', 
      'enableTracking', 
      'trackingSettings'
    ], function(result) {
      if (result.mcpServerUrl) {
        document.getElementById('serverUrl').value = result.mcpServerUrl;
      }
      
      if (result.userName) {
        document.getElementById('userName').value = result.userName;
      }
      
      document.getElementById('autoConnect').checked = !!result.autoConnect;
      
      // Load activity tracking settings
      document.getElementById('enableTracking').checked = 
        result.enableTracking === undefined ? true : !!result.enableTracking;
      
      // Load individual tracking settings
      const trackingSettings = result.trackingSettings || {};
      document.getElementById('trackPageNavigation').checked = 
        trackingSettings.pageNavigation === undefined ? true : !!trackingSettings.pageNavigation;
      document.getElementById('trackClicks').checked = 
        trackingSettings.clicks === undefined ? true : !!trackingSettings.clicks;
      document.getElementById('trackFormInput').checked = 
        trackingSettings.formInput === undefined ? true : !!trackingSettings.formInput;
      document.getElementById('trackScrolling').checked = 
        trackingSettings.scrolling === undefined ? true : !!trackingSettings.scrolling;
      document.getElementById('trackTimeSpent').checked = 
        trackingSettings.timeSpent === undefined ? true : !!trackingSettings.timeSpent;
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
    const trackingOptions = document.querySelectorAll(
      '#trackPageNavigation, #trackClicks, #trackFormInput, #trackScrolling, #trackTimeSpent'
    );
    
    trackingOptions.forEach(option => {
      option.disabled = !trackingEnabled;
    });
  });
  
  // Load settings when the page opens
  document.addEventListener('DOMContentLoaded', function() {
    loadSettings();
    
    // Initialize tracking options state based on master toggle
    const trackingEnabled = document.getElementById('enableTracking').checked;
    const trackingOptions = document.querySelectorAll(
      '#trackPageNavigation, #trackClicks, #trackFormInput, #trackScrolling, #trackTimeSpent'
    );
    
    trackingOptions.forEach(option => {
      option.disabled = !trackingEnabled;
    });
  });