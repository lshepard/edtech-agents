This is a set of tools to allow a centralized Teacher system to control Student computers. We assume students are running Chromebooks.

### Student Browser Extension

To install the Student chrome extension:

1. Open Chrome and go to chrome://extensions/
2. Enable "Developer mode" (toggle in the top-right corner)
3. Click "Load unpacked"
4. Navigate to and select the extension folder



### Student MCP Server

The Student MCP Server is a WebSocket server that runs on student machines to receive commands from the teacher system.

#### Installation

1. Install [uv](https://github.com/astral-sh/uv) if you haven't already.

2. Install dependencies using uv:
   ```bash
   uv pip install -e .
   ```

#### Running the Server

1. Start the server:
   ```bash
   python mcp_server.py
   ```

2. The server will start on port 8090 and log activity to `mcp_server.log`
3. Use the command interface to send commands to connected clients
4. Press Ctrl+C to stop the server

