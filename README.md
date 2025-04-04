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

### Teacher Service

The Teacher Service allows educators to control and monitor student browsers, plan activities, and more.

#### Installation

1. Make sure you have [uv](https://github.com/astral-sh/uv) installed.

2. Navigate to the teacher-service directory:
   ```bash
   cd teacher-service
   ```

3. Install dependencies:
   ```bash
   uv pip install -e .
   ```

#### Running the Server

1. Start the server using Uvicorn:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 3030 --reload
   ```

2. The server will be available at http://localhost:3030
3. API endpoints are accessible at http://localhost:3030/api/

