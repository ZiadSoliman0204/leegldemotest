"""
Document routes for Law Firm AI Assistant
Handles document upload, processing, and indexing for RAG with local embeddings
Enhanced with comprehensive audit logging
"""

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
import time
import uuid
import hashlib
import logging
from typing import List

from ..models import (
    DocumentUploadResponse, 
    SearchRequest, 
    SearchResponse,
    ErrorResponse
)
from ..services.rag_service import LocalRAGService

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize services
rag_service = LocalRAGService()

def get_client_ip(request: Request) -> str:
    """Extract client IP address from request"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    if request.client:
        return request.client.host
    
    return "unknown"

def hash_content(content: str) -> str:
    """Create SHA-256 hash of content for audit trail"""
    return hashlib.sha256(content.encode()).hexdigest()[:16]

def log_document_audit(
    action_type: str,
    status: str,
    details: str,
    ip_address: str = "",
    user_agent: str = "",
    resource: str = "",
    content_hash: str = "",
    severity_level: str = "INFO",
    request_id: str = ""
):
    """Log document-related audit events"""
    try:
        logger.info(
            f"AUDIT_LOG: action_type={action_type}, status={status}, "
            f"resource={resource}, ip_address={ip_address}, "
            f"user_agent={user_agent}, content_hash={content_hash}, "
            f"severity_level={severity_level}, request_id={request_id}, "
            f"details={details}"
        )
    except Exception as e:
        logger.error(f"Failed to log audit event: {e}")

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...), request: Request = None):
    """
    Upload and process a legal document for RAG indexing
    Supports PDF, TXT, and DOCX files with local processing
    Enhanced with comprehensive audit logging
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Extract request metadata
    ip_address = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown") if request else "unknown"
    
    # Log document upload initiation
    log_document_audit(
        action_type="DOC_UPLOAD_INITIATED",
        status="initiated",
        details=f"Document upload started. Filename: {file.filename}, "
               f"Content-Type: {file.content_type}, Size: {file.size if hasattr(file, 'size') else 'unknown'} bytes",
        ip_address=ip_address,
        user_agent=user_agent,
        resource=f"document:{file.filename}",
        severity_level="INFO",
        request_id=request_id
    )
    
    try:
        # Validate file type
        allowed_types = {
            'application/pdf': '.pdf',
            'text/plain': '.txt',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
        }
        
        if not file.content_type or file.content_type not in allowed_types:
            # Log validation failure
            log_document_audit(
                action_type="DOC_UPLOAD_VALIDATION_FAILED",
                status="failure",
                details=f"Unsupported file type: {file.content_type}. "
                       f"Allowed: {', '.join(allowed_types.values())}",
                ip_address=ip_address,
                user_agent=user_agent,
                resource=f"document:{file.filename}",
                severity_level="WARNING",
                request_id=request_id
            )
            
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported formats: {', '.join(allowed_types.values())}"
            )
        
        logger.info(f"Processing document upload: {file.filename} ({file.content_type})")
        
        # Read file content
        file_content = await file.read()
        file_hash = hash_content(file_content.decode('latin-1', errors='ignore'))
        
        # Log file processing start
        log_document_audit(
            action_type="DOC_PROCESSING_STARTED",
            status="initiated",
            details=f"Started processing document. Content hash: {file_hash}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource=f"document:{file.filename}",
            content_hash=file_hash,
            severity_level="INFO",
            request_id=request_id
        )
        
        # Process and upload document using local service
        result = rag_service.upload_document(
            file_content=file_content,
            filename=file.filename
        )
        
        processing_time = time.time() - start_time
        
        # Log successful upload
        log_document_audit(
            action_type="DOC_UPLOAD_SUCCESS",
            status="success",
            details=f"Document processed successfully. Processing time: {processing_time:.2f}s, "
                   f"Document ID: {result['document_id']}, Pages: {result['pages_processed']}, "
                   f"Chunks created: {result.get('chunk_count', 'unknown')}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource=f"document:{file.filename}",
            content_hash=file_hash,
            severity_level="INFO",
            request_id=request_id
        )
        
        logger.info(f"Document {file.filename} processed successfully in {processing_time:.2f}s")
        
        return DocumentUploadResponse(
            document_id=result["document_id"],
            filename=result["filename"],
            pages_processed=result["pages_processed"],
            status="success",
            processing_time=processing_time
        )
        
    except ValueError as ve:
        processing_time = time.time() - start_time
        error_msg = str(ve)
        
        # Log validation error
        log_document_audit(
            action_type="DOC_UPLOAD_VALIDATION_ERROR",
            status="error",
            details=f"Validation error after {processing_time:.2f}s: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource=f"document:{file.filename}",
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(f"Validation error for document {file.filename}: {error_msg}")
        raise HTTPException(
            status_code=400,
            detail=error_msg
        )
    except Exception as e:
        processing_time = time.time() - start_time
        error_msg = str(e)
        
        # Log processing error
        log_document_audit(
            action_type="DOC_UPLOAD_ERROR",
            status="error",
            details=f"Processing error after {processing_time:.2f}s: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource=f"document:{file.filename}",
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(f"Error processing document {file.filename}: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {error_msg}"
        )

@router.post("/search", response_model=SearchResponse)
async def search_documents(request_data: SearchRequest, request: Request = None):
    """
    Search indexed documents using local vector similarity
    Returns relevant document chunks based on query
    Enhanced with comprehensive audit logging
    """
    start_time = time.time()
    request_id = str(uuid.uuid4())
    
    # Extract request metadata
    ip_address = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown") if request else "unknown"
    
    # Hash the search query for audit trail
    query_hash = hash_content(request_data.query)
    
    # Log search initiation
    log_document_audit(
        action_type="DOC_SEARCH_INITIATED",
        status="initiated",
        details=f"Document search initiated. Query length: {len(request_data.query)} chars, "
               f"Top-K: {request_data.top_k}",
        ip_address=ip_address,
        user_agent=user_agent,
        resource="document_search",
        content_hash=query_hash,
        severity_level="INFO",
        request_id=request_id
    )
    
    try:
        logger.info(f"Searching documents for query: {request_data.query[:100]}...")
        
        # Perform local vector search
        search_results = rag_service.search_documents(
            query=request_data.query,
            n_results=request_data.top_k
        )
        
        # Filter by threshold if specified
        original_count = len(search_results)
        if hasattr(request_data, 'threshold') and request_data.threshold:
            search_results = [
                result for result in search_results 
                if result.get('similarity', 0.0) >= request_data.threshold
            ]
        
        query_time = time.time() - start_time
        
        # Log successful search
        sources_found = [result.get('metadata', {}).get('filename', 'Unknown') for result in search_results]
        log_document_audit(
            action_type="DOC_SEARCH_SUCCESS",
            status="success",
            details=f"Search completed in {query_time:.2f}s. Results: {len(search_results)}/{original_count}, "
                   f"Sources: {', '.join(set(sources_found))}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="document_search",
            content_hash=query_hash,
            severity_level="INFO",
            request_id=request_id
        )
        
        logger.info(f"Search completed: {len(search_results)} results in {query_time:.2f}s")
        
        # Convert to expected format
        formatted_results = []
        for result in search_results:
            formatted_results.append({
                "content": result["content"],
                "metadata": result["metadata"],
                "similarity_score": result["similarity"]
            })
        
        return SearchResponse(
            results=formatted_results,
            total_results=len(formatted_results),
            query_time=query_time
        )
        
    except Exception as e:
        query_time = time.time() - start_time
        error_msg = str(e)
        
        # Log search error
        log_document_audit(
            action_type="DOC_SEARCH_ERROR",
            status="error",
            details=f"Search error after {query_time:.2f}s: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="document_search",
            content_hash=query_hash,
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(f"Error searching documents: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search documents: {error_msg}"
        )

@router.get("/list")
async def list_documents(request: Request = None):
    """
    List all indexed documents with metadata
    Returns document information from ChromaDB
    Enhanced with audit logging
    """
    request_id = str(uuid.uuid4())
    
    # Extract request metadata
    ip_address = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown") if request else "unknown"
    
    # Log document list access
    log_document_audit(
        action_type="DOC_LIST_ACCESSED",
        status="initiated",
        details="User accessed document list",
        ip_address=ip_address,
        user_agent=user_agent,
        resource="document_list",
        severity_level="INFO",
        request_id=request_id
    )
    
    try:
        documents = rag_service.list_documents()
        
        # Log successful list retrieval
        log_document_audit(
            action_type="DOC_LIST_SUCCESS",
            status="success",
            details=f"Document list retrieved successfully. Count: {len(documents)}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="document_list",
            severity_level="INFO",
            request_id=request_id
        )
        
        return {"documents": documents}
        
    except Exception as e:
        error_msg = str(e)
        
        # Log list error
        log_document_audit(
            action_type="DOC_LIST_ERROR",
            status="error",
            details=f"Error retrieving document list: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="document_list",
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(f"Error listing documents: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {error_msg}"
        )

@router.delete("/{document_id}")
async def delete_document(document_id: str, request: Request = None):
    """
    Delete a document and its associated chunks from the index
    Removes all vectors and metadata for the specified document
    Enhanced with comprehensive audit logging
    """
    request_id = str(uuid.uuid4())
    
    # Extract request metadata
    ip_address = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown") if request else "unknown"
    
    # Log document deletion attempt
    log_document_audit(
        action_type="DOC_DELETE_INITIATED",
        status="initiated",
        details=f"Document deletion initiated for ID: {document_id}",
        ip_address=ip_address,
        user_agent=user_agent,
        resource=f"document:{document_id}",
        severity_level="INFO",
        request_id=request_id
    )
    
    try:
        logger.info(f"Deleting document: {document_id}")
        
        success = rag_service.delete_document(document_id)
        
        if success:
            # Log successful deletion
            log_document_audit(
                action_type="DOC_DELETE_SUCCESS",
                status="success",
                details=f"Document {document_id} deleted successfully",
                ip_address=ip_address,
                user_agent=user_agent,
                resource=f"document:{document_id}",
                severity_level="INFO",
                request_id=request_id
            )
            
            return {
                "status": "success",
                "message": f"Document {document_id} deleted successfully"
            }
        else:
            # Log document not found
            log_document_audit(
                action_type="DOC_DELETE_NOT_FOUND",
                status="failure",
                details=f"Document {document_id} not found for deletion",
                ip_address=ip_address,
                user_agent=user_agent,
                resource=f"document:{document_id}",
                severity_level="WARNING",
                request_id=request_id
            )
            
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        
        # Log deletion error
        log_document_audit(
            action_type="DOC_DELETE_ERROR",
            status="error",
            details=f"Error deleting document {document_id}: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource=f"document:{document_id}",
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(f"Error deleting document {document_id}: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {error_msg}"
        )

@router.get("/stats")
async def get_collection_stats(request: Request = None):
    """
    Get statistics about the document collection
    Returns counts and metadata about indexed documents
    Enhanced with audit logging
    """
    request_id = str(uuid.uuid4())
    
    # Extract request metadata
    ip_address = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown") if request else "unknown"
    
    # Log stats access
    log_document_audit(
        action_type="DOC_STATS_ACCESSED",
        status="initiated",
        details="User accessed document collection statistics",
        ip_address=ip_address,
        user_agent=user_agent,
        resource="document_stats",
        severity_level="INFO",
        request_id=request_id
    )
    
    try:
        stats = rag_service.get_collection_stats()
        
        # Log successful stats retrieval
        log_document_audit(
            action_type="DOC_STATS_SUCCESS",
            status="success",
            details=f"Document stats retrieved: {stats.get('total_documents', 'unknown')} docs, "
                   f"{stats.get('total_chunks', 'unknown')} chunks",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="document_stats",
            severity_level="INFO",
            request_id=request_id
        )
        
        return stats
        
    except Exception as e:
        error_msg = str(e)
        
        # Log stats error
        log_document_audit(
            action_type="DOC_STATS_ERROR",
            status="error",
            details=f"Error retrieving document stats: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="document_stats",
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(f"Error getting collection stats: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get collection stats: {error_msg}"
        )

@router.get("/health")
async def get_rag_health(request: Request = None):
    """
    Check the health of the RAG service and vector database
    Enhanced with audit logging
    """
    request_id = str(uuid.uuid4())
    
    # Extract request metadata
    ip_address = get_client_ip(request) if request else "unknown"
    user_agent = request.headers.get("User-Agent", "unknown") if request else "unknown"
    
    # Log health check access
    log_document_audit(
        action_type="RAG_HEALTH_CHECK",
        status="initiated",
        details="RAG service health check requested",
        ip_address=ip_address,
        user_agent=user_agent,
        resource="rag_health",
        severity_level="INFO",
        request_id=request_id
    )
    
    try:
        health_status = rag_service.health_check()
        
        # Determine severity based on health status
        severity = "INFO" if health_status.get("status") == "healthy" else "WARNING"
        
        # Log health check result
        log_document_audit(
            action_type="RAG_HEALTH_CHECK_RESULT",
            status="success",
            details=f"RAG health check completed. Status: {health_status.get('status', 'unknown')}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="rag_health",
            severity_level=severity,
            request_id=request_id
        )
        
        return health_status
        
    except Exception as e:
        error_msg = str(e)
        
        # Log health check error
        log_document_audit(
            action_type="RAG_HEALTH_CHECK_ERROR",
            status="error",
            details=f"RAG health check failed: {error_msg}",
            ip_address=ip_address,
            user_agent=user_agent,
            resource="rag_health",
            severity_level="ERROR",
            request_id=request_id
        )
        
        logger.error(f"Error checking RAG health: {error_msg}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to check RAG health: {error_msg}"
        ) 