"""
LLM Client Service for Law Firm AI Assistant
Handles communication with remote LLaMA 3 70B model via OpenAI-compatible API
"""

import httpx
import asyncio
from typing import Dict, Any, List, Optional
from loguru import logger

from ..config import settings

class LLMClient:
    """
    Client for communicating with remote LLM API
    Uses OpenAI-compatible endpoint format for CoreWeave VLLM
    """
    
    def __init__(self):
        self.api_url = settings.LLM_API_URL
        self.api_key = settings.LLM_API_KEY
        self.model_name = settings.LLM_MODEL_NAME
        self.timeout = settings.REQUEST_TIMEOUT
        
        # Validate configuration
        if not self.api_url or not self.api_key:
            logger.warning("LLM API not fully configured - check environment variables")
    
    async def chat_completion(
        self, 
        message: str = None,
        messages: Optional[List[Dict[str, str]]] = None, 
        max_tokens: int = 2048, 
        temperature: float = 0.7,
        system_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send chat completion request to remote LLM
        
        Args:
            message: User's input message (deprecated, use messages instead)
            messages: Full conversation history in OpenAI format
            max_tokens: Maximum tokens in response
            temperature: Response creativity (0.0-1.0)
            system_message: Optional system prompt
            
        Returns:
            Dictionary containing response content and metadata
        """
        if not self.api_url or not self.api_key:
            raise ValueError("LLM API not configured - check LLM_API_URL and LLM_API_KEY")
        
        # Prepare messages in OpenAI format
        if messages:
            # Use provided conversation history
            formatted_messages = []
            
            # Add system message at the beginning if provided
            if system_message:
                formatted_messages.append({"role": "system", "content": system_message})
            else:
                # Default system message for legal assistant
                formatted_messages.append({
                    "role": "system", 
                    "content": "You are a helpful AI assistant for legal professionals. Provide accurate, professional responses based on the provided context and legal knowledge."
                })
            
            # Add conversation history
            formatted_messages.extend(messages)
        else:
            # Fallback to single message format for backward compatibility
            formatted_messages = []
            
            if system_message:
                formatted_messages.append({"role": "system", "content": system_message})
            else:
                # Default system message for legal assistant
                formatted_messages.append({
                    "role": "system", 
                    "content": "You are a helpful AI assistant for legal professionals. Provide accurate, professional responses based on the provided context and legal knowledge."
                })
            
            if message:
                formatted_messages.append({"role": "user", "content": message})
        
        # Prepare request payload
        payload = {
            "model": self.model_name,
            "messages": formatted_messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                logger.info(f"Sending request to LLM API: {self.api_url}")
                
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers=headers
                )
                
                response.raise_for_status()
                result = response.json()
                
                # Extract content from OpenAI-compatible response
                if "choices" in result and len(result["choices"]) > 0:
                    content = result["choices"][0]["message"]["content"]
                    usage = result.get("usage", {})
                    
                    return {
                        "content": content,
                        "usage": usage,
                        "model": result.get("model", self.model_name)
                    }
                else:
                    raise ValueError("Invalid response format from LLM API")
                    
        except httpx.TimeoutException:
            logger.error("Timeout occurred while calling LLM API")
            raise Exception("LLM API request timed out")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error from LLM API: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM API returned error: {e.response.status_code}")
            
        except Exception as e:
            logger.error(f"Unexpected error calling LLM API: {str(e)}")
            raise Exception(f"Failed to call LLM API: {str(e)}")
    
    async def list_models(self) -> List[str]:
        """
        List available models from the remote API
        
        Returns:
            List of available model names
        """
        if not self.api_url or not self.api_key:
            raise ValueError("LLM API not configured")
        
        # Construct models endpoint URL
        models_url = self.api_url.replace("/chat/completions", "/models")
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                response = await client.get(models_url, headers=headers)
                response.raise_for_status()
                result = response.json()
                
                if "data" in result:
                    return [model["id"] for model in result["data"]]
                else:
                    return [self.model_name]  # Fallback to configured model
                    
        except Exception as e:
            logger.warning(f"Could not retrieve models list: {str(e)}")
            return [self.model_name]  # Fallback to configured model
    
    async def health_check(self) -> bool:
        """
        Check if the LLM API is accessible and responding
        
        Returns:
            True if API is healthy, False otherwise
        """
        try:
            # Simple test request
            test_response = await self.chat_completion(
                message="Hello, this is a health check.",
                max_tokens=10,
                temperature=0.1
            )
            return bool(test_response.get("content"))
            
        except Exception as e:
            logger.error(f"LLM API health check failed: {str(e)}")
            return False 