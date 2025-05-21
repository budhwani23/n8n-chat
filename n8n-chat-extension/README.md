# n8n Chat Chrome Extension

A chatbot Chrome extension that uses LLMs (via LangChain backend) to generate n8n workflows and answer questions.

## Features
- Chat with various LLMs (Groq, OpenAI, Gemini, OpenRouter, Cerebras, etc.)
- Generates n8n workflow JSONs on request
- Clean, modern chat UI

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