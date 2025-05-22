# n8n Chat Chrome Extension

A chatbot Chrome extension that uses LLMs (via LangChain backend) to generate n8n workflows and answer questions.

## Features
- Chat with various LLMs (Groq, OpenAI, Gemini, OpenRouter, Cerebras, etc.)
- Generates n8n workflow JSONs on request
- Clean, modern chat UI

### AI-Powered n8n Workflow Creation
- **Usage**: You can ask the chat assistant to create n8n workflows for you using natural language.
- **Activation Phrases**: Start your message with phrases like 'create workflow:', 'build workflow:', or 'generate workflow:'.
- **Example**: `create workflow: when a new email arrives in Gmail, send its subject to a Slack channel named #notifications`
- **Process**: The assistant will attempt to generate the workflow JSON and then try to create it directly in your configured n8n instance using its API.
- **Feedback**: You'll receive feedback on success or failure. This can include:
    - A success message with a link to view the created workflow in your n8n instance.
    - An error message if the n8n API call fails, often with the generated JSON and an option to import it manually.
    - The raw JSON if the LLM fails to generate a valid structure that can be sent to the n8n API.
- **Backend Configuration Note**: This feature requires the backend server (`n8n-chat-backend`) to be correctly configured with your n8n instance's base URL (`N8N_BASE_URL`) and a valid n8n API key (`N8N_API_KEY`). See the backend's README file for detailed setup instructions.

## Setup

### 1. Backend Server
This extension requires a backend server running LangChain to connect to LLM APIs. See `../n8n-chat-backend/README.md` for setup.

### 2. Load the Extension in Chrome
1. Build or download the backend server and start it (default: http://localhost:5000).
2. In Chrome, go to `chrome://extensions/`.
3. Enable "Developer mode" (top right).
4. Click "Load unpacked" and select the `n8n-chat-extension` folder.
5. Add your own icon at `icons/icon.png` (128x128 PNG).
6. Click the extension icon to open the chat popup.

## Configuration
- The extension expects the backend at `http://localhost:5000/chat`. You can change this in `popup.js` if needed.

---

For backend setup, see the `n8n-chat-backend` folder. 