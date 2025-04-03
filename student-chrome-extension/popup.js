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