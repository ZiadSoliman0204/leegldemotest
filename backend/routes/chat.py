"""
Chat routes for Law Firm AI Assistant
Handles user prompts and routes to remote LLM with RAG integration
"""

from fastapi import APIRouter, HTTPException, Depends
import httpx
import time
from loguru import logger
from typing import Optional

from ..models import ChatRequest, ChatResponse, ErrorResponse
from ..config import settings
from ..services.llm_client import LLMClient
from ..services.rag_service import LocalRAGService

router = APIRouter()

# Initialize services
llm_client = LLMClient()
rag_service = LocalRAGService()

@router.post("/completions", response_model=ChatResponse)
async def chat_completion(request: ChatRequest):
    """
    Process user prompt and return LLM response with optional RAG context
    Routes the request to remote LLaMA 3 70B model via OpenAI-compatible API
    """
    start_time = time.time()
    
    try:
        # Get RAG context if requested
        context = None
        sources = None
        if request.use_rag and request.message:
            logger.info(f"Retrieving RAG context for query: {request.message[:100]}...")
            context_results = rag_service.search_documents(
                query=request.message,
                n_results=5
            )
            
            # Filter by similarity threshold
            filtered_results = [
                result for result in context_results 
                if result.get('similarity', 0.0) >= 0.7
            ]
            
            if filtered_results:
                context = "\n\n".join([
                    f"[Source: {result['metadata'].get('filename', 'Unknown')}]\n{result['content']}"
                    for result in filtered_results
                ])
                sources = [result['metadata'].get('filename', 'Unknown') for result in filtered_results]
                logger.info(f"Found {len(filtered_results)} relevant documents")
            else:
                logger.info("No relevant documents found in RAG search")
        
        # Prepare the enhanced prompt with context
        enhanced_message = request.message
        if context:
            enhanced_message = f"""Based on the following legal documents and context, please answer the question:

CONTEXT:
{context}

QUESTION: {request.message}

Please provide a comprehensive answer based on the provided documents. If the documents don't contain relevant information, please indicate this clearly."""
        
        # Call the remote LLM
        logger.info("Sending request to remote LLM API")
        llm_response = await llm_client.chat_completion(
            message=enhanced_message,
            max_tokens=request.max_tokens or settings.MAX_TOKENS,
            temperature=request.temperature or settings.TEMPERATURE
        )
        
        processing_time = time.time() - start_time
        logger.info(f"Request processed in {processing_time:.2f} seconds")
        
        return ChatResponse(
            response=llm_response.get("content", ""),
            sources=sources,
            token_usage=llm_response.get("usage"),
            processing_time=processing_time
        )
        
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error in chat completion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )

@router.post("/stream", response_model=ChatResponse)
async def chat_completion_stream(request: ChatRequest):
    """
    Stream chat completion for real-time responses
    Currently returns full response - can be enhanced for true streaming
    """
    # For now, delegate to regular completion
    # This can be enhanced later for true streaming with Server-Sent Events
    return await chat_completion(request)

@router.get("/models")
async def list_available_models():
    """List available models from the remote LLM API"""
    try:
        models = await llm_client.list_models()
        return {"models": models}
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve models: {str(e)}"
        ) 