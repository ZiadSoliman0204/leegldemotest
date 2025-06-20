"""
Document routes for Law Firm AI Assistant
Handles document upload, processing, and indexing for RAG with local embeddings
"""

from fastapi import APIRouter, UploadFile, File, HTTPException
import time
import uuid
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

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a legal document for RAG indexing
    Supports PDF, TXT, and DOCX files with local processing
    """
    start_time = time.time()
    
    try:
        # Validate file type
        allowed_types = {
            'application/pdf': '.pdf',
            'text/plain': '.txt',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx'
        }
        
        if not file.content_type or file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type. Supported formats: {', '.join(allowed_types.values())}"
            )
        
        logger.info(f"Processing document upload: {file.filename} ({file.content_type})")
        
        # Read file content
        file_content = await file.read()
        
        # Process and upload document using local service
        result = rag_service.upload_document(
            file_content=file_content,
            filename=file.filename
        )
        
        processing_time = time.time() - start_time
        
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
        logger.error(f"Validation error for document {file.filename}: {str(ve)}")
        raise HTTPException(
            status_code=400,
            detail=str(ve)
        )
    except Exception as e:
        processing_time = time.time() - start_time
        logger.error(f"Error processing document {file.filename}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )

@router.post("/search", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Search indexed documents using local vector similarity
    Returns relevant document chunks based on query
    """
    start_time = time.time()
    
    try:
        logger.info(f"Searching documents for query: {request.query[:100]}...")
        
        # Perform local vector search
        search_results = rag_service.search_documents(
            query=request.query,
            n_results=request.top_k
        )
        
        # Filter by threshold if specified
        if hasattr(request, 'threshold') and request.threshold:
            search_results = [
                result for result in search_results 
                if result.get('similarity', 0.0) >= request.threshold
            ]
        
        query_time = time.time() - start_time
        
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
        logger.error(f"Error searching documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to search documents: {str(e)}"
        )

@router.get("/list")
async def list_documents():
    """
    List all indexed documents with metadata
    Returns document information from ChromaDB
    """
    try:
        documents = rag_service.list_documents()
        return {"documents": documents}
        
    except Exception as e:
        logger.error(f"Error listing documents: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(e)}"
        )

@router.delete("/{document_id}")
async def delete_document(document_id: str):
    """
    Delete a document and its associated chunks from the index
    Removes all vectors and metadata for the specified document
    """
    try:
        logger.info(f"Deleting document: {document_id}")
        
        success = rag_service.delete_document(document_id)
        
        if success:
            return {
                "status": "success",
                "message": f"Document {document_id} deleted successfully"
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"Document {document_id} not found"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting document {document_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )

@router.get("/stats")
async def get_collection_stats():
    """
    Get statistics about the document collection
    Returns counts and metadata about indexed documents
    """
    try:
        stats = rag_service.get_collection_stats()
        return stats
        
    except Exception as e:
        logger.error(f"Error getting collection stats: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get collection stats: {str(e)}"
        )

@router.get("/health")
async def get_rag_health():
    """
    Check the health of the RAG service
    Returns status of local embedding service and document storage
    """
    try:
        health_status = rag_service.health_check()
        return health_status
        
    except Exception as e:
        logger.error(f"Error getting RAG health: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get RAG health: {str(e)}"
        ) 