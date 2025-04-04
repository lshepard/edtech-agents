This is a prototype of a technique that may allow a centralized Teacher AI to control and launch Student activities on Chrome browsers.

### Install Student Browser Extension

| :exclamation:  Note: there are no security or privacy controls yet as this is a prototype. Uninstall the extension when not using.  |
|---|

#### On a Computer

1. Visit [the Extension Google Drive folder](https://drive.google.com/drive/folders/18h69GwZal5CADhOhvipcbSvmBITgnrod)

2. Select Download to download the whole folder as a zip
![image](https://github.com/user-attachments/assets/aafaa564-797c-4164-88de-c8f4349b48d5)

3. Unzip the folder on your local machine
4. Open Chrome and go to chrome://extensions/
5. Enable "Developer mode" (toggle in the top-right corner)
6. Click "Load unpacked"
7. Navigate to and select the extension folder
   
#### On a Chromebook

1. Visit [the Extension Google Drive folder](https://drive.google.com/drive/folders/18h69GwZal5CADhOhvipcbSvmBITgnrod).
2. Click Add to My Drive
3. Open Chrome and go to chrome://extensions/
4. Enable "Developer mode" (toggle in the top-right corner)
5. Click "Load unpacked"
6. Select the Extension Drive Folder from My Drive

You should see the extension in your extensions page.

![image](https://github.com/user-attachments/assets/9641dda9-d6fc-40b6-b0ad-5d79eee065e0)

#### Using the Extension

The extension helps you connect to the server to receive activities. I suggest you pin it to your header:

![image](https://github.com/user-attachments/assets/546b7127-ae40-4bff-bb80-bb0776ee1d04)

You can check server connection status:

![image](https://github.com/user-attachments/assets/1d775f65-976a-4287-912c-29359c173adb)

Click on the Settings page, and enter your name to identify yourself to the server

![image](https://github.com/user-attachments/assets/544ff3be-aefc-45a1-adb8-9f43bbd9bd32)

Then click on the icon in the extensions bar and click Connect. You may need to refresh a few times.

When successful, you'll see it connected:
![image](https://github.com/user-attachments/assets/c9c433f0-fdc5-40ba-98cf-704f04534df4)


## Using the Teacher App

Visit https://app.learninghelper.org/.

On the initial page you can see who is currently connected, and begin planning an activity.

![image](https://github.com/user-attachments/assets/04bca440-ab22-4d9b-b9f2-3e0c1bf96c8d)

### Plan An Activity

Enter the student grade and free text describing what you'd like to teach, then click **Plan Activity**.

![image](https://github.com/user-attachments/assets/447c1601-7224-445f-b014-7a8f894d4781)

The app has access to a set of resources pulled from education sites such as Khan Academy. (You can view the full set of resources here](https://github.com/lshepard/edtech-agents/tree/main/context). It will prefer to load those, but if it cannot find anything that fits, then it will search the web for similar exercises.

After a minute or two, you'll see the suggested activities:

![image](https://github.com/user-attachments/assets/d1d49157-b745-4f7f-9ffa-8a03d905d5dd)

### Launching an Activity

If a browser is connected, you will see it in the dropdown. You can select the browser where you want to launch an activity, then click **Launch Activity**

![image](https://github.com/user-attachments/assets/47fcd97c-592c-4f0a-833e-24acc216d66d)

In the **Student Activity Log** at the bottom of the page, you'll see a screenshot of their screen to confirm that the activity launched successfully.

You can click **Take New Screenshot** at any time to see what they are currently working on.


# Development


These are instructions for how to run the server locally.


#### Environment Variables

Create a `.env` file in the root with these variables:

```
OPENAI_API_KEY=xxx
TAVILY_API_KEY=xxx
LANGCHAIN_TRACING_V2=true
LANGCHAIN_ENDPOINT="https://api.smith.langchain.com"
LANGCHAIN_PROJECT="flourish"
LANGCHAIN_API_KEY=xxx
```

The LANGCHAIN keys are optional.

To pass environment variables to the container:
```bash
docker run -p 3030:3030 -p 8090:8090 -e API_KEY=yourkey -e OTHER_VAR=value teacher-service
```

#### Installation

1. Install [uv](https://github.com/astral-sh/uv) if you haven't already.

2. Create a virtual environment

   ```bash
   uv venv
   source .venv/bin/activate
   ```

3. Install dependencies using uv:
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
4. The websock service is available at your IP address port 8090, i.e. ws://192.168.1.3:8090

### Docker Deployment

The Teacher Service can be deployed using Docker for easier setup and consistent environments.

#### Building the Docker Image

1. Build the Docker image:
   ```bash
   docker build -t teacher-service .
   ```

#### Running with Docker

1. Run the container:
   ```bash
   docker run -p 3030:3030 -p 8090:8090 teacher-service
   ```

   This will start the application using:
   ```
   uvicorn app.main:app --reload --port 3030 --host 0.0.0.0
   ```

2. The server will be available at http://localhost:3030
3. The WebSocket server will be available on port 8090
