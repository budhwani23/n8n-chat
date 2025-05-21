from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Callable
import json
import logging
from functools import lru_cache

# LLM imports
from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_cerebras import ChatCerebras

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

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
    keywords = ["workflow", "n8n", "automation", "automate", "create flow"]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in keywords)

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
        prompt = (
            f"You are an expert in n8n. When asked to build something, generate a valid n8n workflow JSON for the request. "
            f"Only output the JSON, nothing else.\\n\\nUser request: {req.message}" # Use f-string
        )
    try:
        response = llm.invoke([{"role": "user", "content": prompt}])
        reply = getattr(response, "content", None) or getattr(response, "text", None) or str(response)
        
        if is_workflow: # Use stored variable
            try:
                # Attempt to find the start of the JSON object
                json_start_index = reply.find("{")
                json_end_index = reply.rfind("}") + 1
                if json_start_index != -1 and json_end_index > json_start_index:
                    json_str = reply[json_start_index:json_end_index]
                    json_obj = json.loads(json_str)
                    reply = json.dumps(json_obj, indent=2)
                # If not a clear JSON, return as is, or log a warning
                # else:
                #     logger.warning("Workflow request detected, but LLM output was not parsable as JSON.")
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse LLM output as JSON for workflow request: {e}. Raw reply: {reply[:500]}...") # Log part of the reply
                # Decide if you want to return the raw reply or an error
                # For now, returning raw reply as before
            except Exception as e: # Catch other potential errors during JSON processing
                logger.warning(f"Error processing LLM output for workflow: {e}")
                # pass # Or handle more gracefully

        return {"reply": reply}
    except Exception as e:
        logger.error(f"LLM invocation error: {e}")
        return JSONResponse(status_code=500, content={"reply": f"LLM error: {str(e)}"})

# To run: uvicorn main:app --reload --port 5000
