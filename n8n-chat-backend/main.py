from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Callable
import json
import logging
from functools import lru_cache
import os

# LLM imports
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_cerebras import ChatCerebras
import httpx

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# n8n Configuration
N8N_BASE_URL = os.getenv("N8N_BASE_URL", "http://localhost:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY")
if not N8N_API_KEY:
    print("WARNING: N8N_API_KEY environment variable not set. Workflow creation will likely fail.")

# LLM Workflow Generation Prompt Template
LLM_WORKFLOW_PROMPT_TEMPLATE = """
You are an expert n8n workflow automation assistant. Your task is to convert a user's natural language description of a desired automation into a valid n8n workflow JSON object.

The output MUST be a single, valid JSON object adhering to the n8n workflow structure. Do not include any explanatory text before or after the JSON object.

**n8n Workflow JSON Structure Based on Example:**

A workflow has a `name`, an array of `nodes`, an empty `pinData` object, a `connections` object, an `active` status, `settings`, an empty `versionId` string, optional `meta` information, and optional `tags`.

```json
{{
  "name": "<<WORKFLOW_NAME_GENERATED_BY_LLM>>",
  "nodes": [
    {{
      "parameters": {{
        // Node-specific parameters, e.g., "rule" for cron, "path" for webhook
      }},
      "id": "<<UUID_FOR_NODE_1>>",
      "name": "<<DESCRIPTIVE_TRIGGER_NODE_NAME>>",
      "type": "<<N8N_TRIGGER_NODE_TYPE>>",
      "typeVersion": 1,
      "position": [ 800, 200 ]
    }},
    {{
      "parameters": {{
        // Node-specific parameters, e.g., "channel", "text" for Slack
        // If values are missing from user query, use: "<<PLACEHOLDER: Specify Missing Detail e.g., Slack Channel>>"
      }},
      "id": "<<UUID_FOR_NODE_2>>",
      "name": "<<DESCRIPTIVE_ACTION_NODE_NAME>>",
      "type": "<<N8N_ACTION_NODE_TYPE>>",
      "typeVersion": 1,
      "position": [ 1050, 200 ],
      "credentials": {{
        // Optional: Include if node requires credentials.
        // Example: "<<EXPECTED_N8N_CREDENTIAL_KEY_FOR_NODE_TYPE>>": {{ "id": "<<PLACEHOLDER: Your_Credential_ID>>", "name": "My Credential Name" }}
        // If unsure of EXPECTED_N8N_CREDENTIAL_KEY_FOR_NODE_TYPE, use "<<PLACEHOLDER: CredentialTypeKey>>" for that key.
      }}
    }}
    // Add more nodes as required by the user's request.
  ],
  "pinData": {{}},
  "connections": {{
    // Example: "<<UUID_FOR_NODE_1>>": {{ "main": [{{ "node": "<<UUID_FOR_NODE_2>>", "input": "main" }}] }}
    // Connect subsequent nodes as needed.
  }},
  "active": false,
  "settings": {{
    "executionOrder": "v1"
  }},
  "versionId": "",
  "meta": {{
    // "templateCredsRequested": true // Set this if you have included any <<PLACEHOLDER: Your_Credential_ID>>
  }},
  "tags": [
    // {{"name": "<<TAG_NAME>>"}}
  ]
}}
```

**Key Instructions for You (LLM):**
1.  **`name`**: Infer a descriptive name.
2.  **`nodes`**:
    *   Identify Trigger & Actions, map to n8n node types (e.g., `n8n-nodes-base.cron`, `n8n-nodes-base.slack`).
    *   `id`: Generate unique UUIDs.
    *   `name`: Descriptive.
    *   `typeVersion`: Usually 1 or 2. Default to 1 if unsure.
    *   `position`: Arrange logically (e.g., X incrementing: `[800, 200]`, `[1050, 200]`).
    *   `parameters`: Use `"<<PLACEHOLDER: Specify Missing Detail>>"` if user input is incomplete.
    *   `credentials`: Use the format `"<<EXPECTED_N8N_CREDENTIAL_KEY_FOR_NODE_TYPE>>": {{ "id": "<<PLACEHOLDER: Your_Credential_ID>>", "name": "My Credential Name" }}`. If `EXPECTED_N8N_CREDENTIAL_KEY_FOR_NODE_TYPE` is unknown, use `"<<PLACEHOLDER: CredentialTypeKey>>"` for that key.
3.  **`connections`**: Connect nodes, typically `main` output to `main` input.
4.  **`meta`**: If credential placeholders are used, set `"templateCredsRequested": true`.
5.  **Placeholders**: Use `"<<PLACEHOLDER: Descriptive Text>>"` for user-fillable info.

User's request for workflow: "{{USER_NATURAL_LANGUAGE_REQUEST}}"

Convert this request into a single, valid n8n workflow JSON object.
"""

app = FastAPI()

# Allow CORS for local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    """Request model for chat endpoint"""
    message: str = Field(..., description="User message to process")
    provider: str = Field(..., description="LLM provider name")
    apiKey: str = Field(..., description="API key for the provider")

@lru_cache(maxsize=16) # Cache up to 16 LLM instances
def get_llm(provider: str, api_key: str):
    """
    Get the appropriate language model based on the provider.
    
    Args:
        provider: The LLM provider name
        api_key: API key for the provider
        
    Returns:
        An instance of the appropriate LLM class
        
    Raises:
        ValueError: If the provider is not supported
    """
    llm_providers = {
        "openai": lambda: ChatOpenAI(openai_api_key=api_key, model="gpt-3.5-turbo", temperature=0.2),
        "groq": lambda: ChatGroq(api_key=api_key, model="llama3-8b-8192", temperature=0.2),
        "gemini": lambda: ChatGoogleGenerativeAI(api_key=api_key, model="gemini-1.5-pro", temperature=0.2),
        "cerebras": lambda: ChatCerebras(api_key=api_key, model="cerebras-gpt-13b", temperature=0.2)
    }
    
    if provider not in llm_providers:
        raise ValueError(f"Unsupported provider: {provider}. Supported providers: {', '.join(llm_providers.keys())}")
    
    return llm_providers[provider]()

def is_workflow_request(message: str) -> bool:
    """
    Determine if a message is requesting an n8n workflow.
    
    Args:
        message: The user message to analyze
        
    Returns:
        True if the message appears to be requesting an n8n workflow, False otherwise
    """
    message_lower = message.lower()
    prefixes = ["create workflow:", "build workflow:", "generate workflow:"]
    return any(message_lower.startswith(prefix) for prefix in prefixes)

async def create_n8n_workflow(workflow_data: dict) -> dict:
    """
    Creates a workflow in n8n using the provided workflow data.
    """
    if not N8N_API_KEY:
        return {"success": False, "error": "N8N_API_KEY is not configured on the server."}

    api_url = f"{N8N_BASE_URL}/api/v1/workflows"
    headers = {"Authorization": f"X-N8N-API-Key {N8N_API_KEY}"}

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(api_url, json=workflow_data, headers=headers)
            
            if response.status_code == 201 or response.status_code == 200: # 201 is Created, 200 might be returned by some n8n versions
                return {"success": True, "data": response.json()}
            else:
                return {"success": False, "error": f"n8n API Error: {response.status_code} - {response.text}"}
        except httpx.RequestError as e:
            logger.error(f"n8n API request error: {e}")
            return {"success": False, "error": f"n8n API request error: {e}"}
        except json.JSONDecodeError as e: # If n8n responds with non-JSON for some error
            logger.error(f"Failed to decode n8n API JSON response: {e}. Response text: {response.text[:200]}")
            return {"success": False, "error": f"n8n API returned non-JSON response: {response.status_code} - {response.text[:200]}"}
        except Exception as e:
            logger.error(f"Unexpected error calling n8n API: {e}")
            return {"success": False, "error": f"Unexpected error calling n8n API: {e}"}

@app.post("/chat")
async def chat(req: ChatRequest):
    if not req.message or not req.provider or not req.apiKey:
        return JSONResponse(status_code=400, content={"reply": "Missing message, provider, or API key."}) # Use JSONResponse for errors too
    try:
        llm = get_llm(req.provider, req.apiKey)
    except ValueError as e: # Be more specific with exception handling
        logger.error(f"LLM provider error: {e}")
        return JSONResponse(status_code=400, content={"reply": str(e)})
    except Exception as e:
        logger.error(f"Unexpected error getting LLM: {e}")
        return JSONResponse(status_code=500, content={"reply": "Error initializing LLM."})

    prompt = req.message
    is_workflow = is_workflow_request(req.message) # Call once and store

    if is_workflow:
        prompt = LLM_WORKFLOW_PROMPT_TEMPLATE.format(USER_NATURAL_LANGUAGE_REQUEST=req.message)
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        llm_reply_text = getattr(response, "content", None) or getattr(response, "text", None) or str(response)
        
        if is_workflow:
            workflow_json = None
            try:
                # Attempt to find the start of the JSON object and parse it
                json_start_index = llm_reply_text.find("{")
                json_end_index = llm_reply_text.rfind("}") + 1
                if json_start_index != -1 and json_end_index > json_start_index:
                    json_str = llm_reply_text[json_start_index:json_end_index]
                    workflow_json = json.loads(json_str)
                else:
                    # LLM output was not a JSON object as expected
                    error_message = f"LLM output did not contain a valid JSON object. LLM Output: {llm_reply_text}"
                    logger.warning(error_message)
                    return JSONResponse(status_code=200, content={"reply": llm_reply_text, "type": "text", "original_request_type": "workflow"}) # Return raw LLM output if not JSON

            except json.JSONDecodeError as e:
                error_message = f"LLM output was not valid JSON. Error: {e}. LLM Output: {llm_reply_text}"
                logger.warning(error_message)
                # Return the raw LLM output along with an error type for the frontend to handle
                return JSONResponse(status_code=200, content={"reply": llm_reply_text, "type": "text", "original_request_type": "workflow", "parsing_error": str(e)})


            if workflow_json:
                n8n_api_response = await create_n8n_workflow(workflow_json)
                if n8n_api_response["success"]:
                    workflow_id = n8n_api_response.get("data", {}).get("id", "UNKNOWN_ID")
                    created_workflow_data = n8n_api_response.get("data", {})
                    message = f"Successfully created workflow in n8n! Workflow ID: {workflow_id}. You can view it at {N8N_BASE_URL}/workflow/{workflow_id}"
                    logger.info(f"Workflow created: {workflow_id}")
                    return JSONResponse(status_code=200, content={"reply": message, "type": "workflow_created", "workflow_id": workflow_id, "workflow_data": created_workflow_data, "n8n_url": f"{N8N_BASE_URL}/workflow/{workflow_id}"})
                else:
                    error_message = n8n_api_response.get("error", "Unknown error during n8n workflow creation.")
                    logger.error(f"n8n API error: {error_message}")
                    # Return the originally generated JSON along with the API error
                    return JSONResponse(status_code=200, content={"reply": json.dumps(workflow_json, indent=2), "type": "workflow_json_error_api", "error_details": error_message})
            
            # If workflow_json is None due to not finding a JSON object, this part is skipped, handled by earlier return.
            # Fallback for safety, though covered by logic above:
            return JSONResponse(status_code=200, content={"reply": llm_reply_text, "type": "text"})

        # Default non-workflow response
        return JSONResponse(status_code=200, content={"reply": llm_reply_text, "type": "text"})

    except Exception as e:
        logger.error(f"LLM invocation error or other unhandled error: {e}")
        return JSONResponse(status_code=500, content={"reply": f"LLM error: {str(e)}", "type": "error"})

# To run: uvicorn main:app --reload --port 5000
