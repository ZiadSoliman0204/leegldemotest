"""
Chat routes for Law Firm AI Assistant
Handles user prompts and routes to remote LLM with RAG integration
Enhanced with comprehensive audit logging
"""

from fastapi import APIRouter, HTTPException, Depends, Request
import httpx
import time
import hashlib
import uuid
from loguru import logger
from typing import Optional

from ..models import ChatRequest, ChatResponse, ErrorResponse
from ..config import settings
from ..services.llm_client import LLMClient
from ..services.rag_service import LocalRAGService
from ..auth import get_current_user

router = APIRouter()

# Initialize services
llm_client = LLMClient()
rag_service = LocalRAGService()

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    # Check for forwarded headers first (reverse proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct connection
    if request.client:
        return request.client.host
    
    return "unknown"

def hash_content(content: str) -> str:
    """Create SHA-256 hash of content for audit trail"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def log_chat_audit(
    action_type: str,
    status: str,
    details: str,
    ip_address: str = "",
    user_agent: str = "",
    content_hash: str = "",
    severity_level: str = "INFO",
    request_id: str = "",
    resource: str = "chat_completion"
):
    """Log chat-related audit events"""
    try:
        # In a real implementation, this would connect to the database
        # For now, we'll use structured logging that can be parsed
        logger.info(
            f"AUDIT_LOG: action_type={action_type}, status={status}, "
            f"resource={resource}, ip_address={ip_address}, "
            f"user_agent={user_agent}, content_hash={content_hash}, "
            f"severity_level={severity_level}, request_id={request_id}, "
            f"details={details}"
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")

@router.post("/completions", response_model=ChatResponse)
async def chat_completion(
    request: ChatRequest, 
    http_request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Process user prompt and return LLM response with optional RAG context
    Routes the request to remote LLaMA 3 70B model via OpenAI-compatible API
    Enhanced with comprehensive audit logging
    REQUIRES AUTHENTICATION: JWT token or API key
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Extract request metadata
    ip_address = get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "unknown")
    
    # Hash the user prompt for audit trail (security)
    prompt_hash = hash_content(request.message) if request.message else ""
    
    # Log chat initiation
    selected_docs_info = f", selected_docs: {len(request.selected_document_ids)} documents" if request.selected_document_ids else ", selected_docs: all documents"
    log_chat_audit(
        action_type="CHAT_INITIATED",
        status="initiated",
        details=f"Chat request initiated. Message length: {len(request.message)} chars, "
               f"RAG enabled: {request.use_rag}{selected_docs_info}, max_tokens: {request.max_tokens}, "
               f"temperature: {request.temperature}",
        ip_address=ip_address,
        user_agent=user_agent,
        content_hash=prompt_hash,
        severity_level="INFO",
        request_id=request_id
    )
    
    try:
        # Get RAG context if requested
        context = None
        sources = None
        rag_documents_found = 0
        
        if request.use_rag and request.message:
            logger.info(f"Retrieving RAG context for query: {request.message[:100]}...")
            
            # Log RAG query
            log_chat_audit(
                action_type="RAG_QUERY_INITIATED",
                status="initiated",
                details=f"Starting RAG document search for query hash: {prompt_hash}",
                ip_address=ip_address,
                content_hash=prompt_hash,
                severity_level="INFO",
                request_id=request_id,
                resource="rag_service"
            )
            
            context_results = rag_service.search_documents(
                query=request.message,
                n_results=5,
                selected_document_ids=request.selected_document_ids
            )
            
            # Filter by similarity threshold (very low for local TF-IDF embeddings)
            filtered_results = [
                result for result in context_results 
                if result.get('similarity', 0.0) >= 0.001  # Very low threshold for TF-IDF
            ]
            
            rag_documents_found = len(filtered_results)
            
            if filtered_results:
                context = "\n\n".join([
                    f"[Source: {result['metadata'].get('filename', 'Unknown')}]\n{result['content']}"
                    for result in filtered_results
                ])
                sources = [result['metadata'].get('filename', 'Unknown') for result in filtered_results]
                
                # Log successful RAG retrieval
                log_chat_audit(
                    action_type="RAG_QUERY_SUCCESS",
                    status="success",
                    details=f"Found {len(filtered_results)} relevant documents. "
                           f"Sources: {', '.join(sources)}",
                    ip_address=ip_address,
                    content_hash=prompt_hash,
                    severity_level="INFO",
                    request_id=request_id,
                    resource="rag_service"
                )
                
                logger.info(f"Found {len(filtered_results)} relevant documents")
            else:
                # Log no relevant documents found
                log_chat_audit(
                    action_type="RAG_QUERY_NO_RESULTS",
                    status="success",
                    details="No relevant documents found above similarity threshold (0.001)",
                    ip_address=ip_address,
                    content_hash=prompt_hash,
                    severity_level="INFO",
                    request_id=request_id,
                    resource="rag_service"
                )
                
                logger.info("No relevant documents found in RAG search")
        
        # Prepare the enhanced prompt with context
        enhanced_message = request.message
        if context:
            enhanced_message = f"""Based on the following legal documents and context, please answer the question:

CONTEXT:
{context}

QUESTION: {request.message}

Please provide a comprehensive answer based on the provided documents. If the documents don't contain relevant information, please indicate this clearly."""
        
        # Log LLM API call initiation
        log_chat_audit(
            action_type="LLM_API_CALL_INITIATED",
            status="initiated",
            details=f"Sending request to LLM API. Enhanced prompt length: {len(enhanced_message)} chars",
            ip_address=ip_address,
            content_hash=hash_content(enhanced_message),
            severity_level="INFO",
            request_id=request_id,
            resource="llm_api"
        )
        
        # Call the remote LLM
        logger.info("Sending request to remote LLM API")
        llm_response = await llm_client.chat_completion(
            message=enhanced_message,
            max_tokens=request.max_tokens or settings.MAX_TOKENS,
            temperature=request.temperature or settings.TEMPERATURE
        )
        
        processing_time = time.time() - start_time
        
        # Extract token usage info
        token_usage = llm_response.get("usage", {})
        response_content = llm_response.get("content", "")
        
        # Log successful completion
        log_chat_audit(
            action_type="CHAT_COMPLETED",
            status="success",
            details=f"Chat completed successfully. Processing time: {processing_time:.2f}s, "
                   f"Response length: {len(response_content)} chars, "
                   f"Tokens used: {token_usage.get('total_tokens', 'unknown')}, "
                   f"RAG documents: {rag_documents_found}",
            ip_address=ip_address,
            user_agent=user_agent,
            content_hash=prompt_hash,
            severity_level="INFO",
            request_id=request_id
        )
        
        logger.info(f"Request processed in {processing_time:.2f} seconds")
        
        return ChatResponse(
            response=response_content,
            sources=sources,
            token_usage=token_usage,
            processing_time=processing_time
        )
        
    except httpx.RequestError as e:
        processing_time = time.time() - start_time
        error_msg = f"LLM API connection error: {str(e)}"
        
        # Log connection error
        log_chat_audit(
            action_type="CHAT_CONNECTION_ERROR",
            status="error",
            details=f"Connection error after {processing_time:.2f}s: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            content_hash=prompt_hash,
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(error_msg)
        raise HTTPException(
            status_code=503,
            detail="LLM service temporarily unavailable"
        )
    
    except httpx.HTTPStatusError as e:
        processing_time = time.time() - start_time
        error_msg = f"LLM API returned HTTP {e.response.status_code}: {e.response.text}"
        
        # Log HTTP error
        log_chat_audit(
            action_type="CHAT_API_ERROR",
            status="error",
            details=f"API error after {processing_time:.2f}s: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            content_hash=prompt_hash,
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(error_msg)
        raise HTTPException(
            status_code=e.response.status_code,
            detail=f"LLM API error: {e.response.text}"
        )
    
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = f"Unexpected error in chat completion: {str(e)}"
        
        # Log system error
        log_chat_audit(
            action_type="CHAT_SYSTEM_ERROR",
            status="error",
            details=f"System error after {processing_time:.2f}s: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            content_hash=prompt_hash,
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process chat request: {str(e)}"
        )

@router.post("/stream", response_model=ChatResponse)
async def chat_completion_stream(request: ChatRequest, http_request: Request):
    """
    Stream chat completion for real-time responses
    Currently returns full response - can be enhanced for true streaming
    """
    # Log streaming request
    ip_address = get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "unknown")
    prompt_hash = hash_content(request.message) if request.message else ""
    
    log_chat_audit(
        action_type="CHAT_STREAM_INITIATED",
        status="initiated",
        details=f"Streaming chat request initiated. Message length: {len(request.message)} chars",
        ip_address=ip_address,
        user_agent=user_agent,
        content_hash=prompt_hash,
        severity_level="INFO",
        resource="chat_stream"
    )
    
    # For now, delegate to regular completion
    # This can be enhanced later for true streaming with Server-Sent Events
    return await chat_completion(request, http_request)

@router.get("/models")
async def list_available_models(http_request: Request):
    """List available models from the remote LLM API with audit logging"""
    ip_address = get_client_ip(http_request)
    user_agent = http_request.headers.get("User-Agent", "unknown")
    
    # Log models request
    log_chat_audit(
        action_type="LLM_MODELS_REQUESTED",
        status="initiated",
        details="User requested available LLM models list",
        ip_address=ip_address,
        user_agent=user_agent,
        severity_level="INFO",
        resource="llm_models"
    )
    
    try:
        models = await llm_client.list_models()
        
        # Log successful models retrieval
        log_chat_audit(
            action_type="LLM_MODELS_SUCCESS",
            status="success",
            details=f"Successfully retrieved {len(models)} available models",
            ip_address=ip_address,
            user_agent=user_agent,
            severity_level="INFO",
            resource="llm_models"
        )
        
        return {"models": models}
        
    except Exception as e:
        error_msg = f"Error listing models: {str(e)}"
        
        # Log models error
        log_chat_audit(
            action_type="LLM_MODELS_ERROR",
            status="error",
            details=error_msg,
            ip_address=ip_address,
            user_agent=user_agent,
            severity_level="ERROR",
            resource="llm_models"
        )
        
        logger.error(error_msg)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve models: {str(e)}"
        ) 