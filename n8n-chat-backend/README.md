# n8n Chat - Backend

This FastAPI backend powers the n8n Chat extension, providing LLM integration and n8n workflow creation capabilities.

## Setup

### Prerequisites
*   Python 3.8+ (Recommended)
*   Access to an n8n instance (v1.0 or later recommended for API compatibility)
*   API keys for your desired LLM provider(s)

### Installation
1.  Clone the repository (if you haven't already).
2.  Navigate to the `n8n-chat-backend` directory:
    ```bash
    cd n8n-chat-backend
    ```
3.  (Recommended) Create and activate a virtual environment:
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    ```
4.  Install dependencies:
    ```bash
    pip install fastapi uvicorn httpx python-dotenv openai groq # Add other LLM SDKs if used directly
    # Note: Ensure you have the correct LLM provider SDKs installed 
    # based on the providers you intend to use (e.g., openai, groq-python).
    # The application currently dynamically tries to import them based on provider selection.
    ```

### Configuration (Environment Variables)
Create a `.env` file in this `n8n-chat-backend` directory or set the following environment variables before running the server:

*   `N8N_BASE_URL`: The base URL of your n8n instance (e.g., `http://localhost:5678` or `https://your-domain.n8n.cloud`).
    ```
    N8N_BASE_URL="https://your-n8n-instance.com"
    ```
*   `N8N_API_KEY`: Your n8n API key. Generate this from your n8n user settings.
    ```
    N8N_API_KEY="your_n8n_api_key_here"
    ```
*   **LLM Provider API Keys:** At least one LLM provider API key is required.
    *   `OPENAI_API_KEY`: For OpenAI (GPT models).
        ```
        OPENAI_API_KEY="sk-your_openai_api_key_here"
        ```
    *   `GROQ_API_KEY`: For Groq.
        ```
        GROQ_API_KEY="gsk_your_groq_api_key_here"
        ```
    *   `GEMINI_API_KEY`: For Google Gemini (if using a direct Gemini SDK).
    *   `OPENROUTER_API_KEY`: For OpenRouter.
    *   (Add others as supported by the backend's `get_llm_client` function)

**Important:** Add the `.env` file to your project's `.gitignore` if you create it, to avoid committing your API keys.

### Running the Server
Once dependencies are installed and environment variables are set:
```bash
uvicorn main:app --host 0.0.0.0 --port 5000
```
The backend will typically be available at `http://localhost:5000`.

## Features
*   Proxies chat requests to various LLM providers.
*   Parses natural language requests to generate n8n workflow JSON.
*   Uses the n8n API to create workflows directly in your n8n instance.
