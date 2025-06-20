"""
Pydantic models for request/response schemas
Defines data structures for the Law Firm AI Assistant API
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ChatMessage(BaseModel):
    """Individual chat message"""
    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message content")
    timestamp: Optional[datetime] = Field(default_factory=datetime.now)

class ChatRequest(BaseModel):
    """Request for chat completion"""
    message: str = Field(..., description="User's question or prompt")
    context: Optional[str] = Field(None, description="Additional context from RAG")
    use_rag: bool = Field(True, description="Whether to use RAG for context")
    max_tokens: Optional[int] = Field(2048, description="Maximum tokens in response")
    temperature: Optional[float] = Field(0.7, description="Response creativity (0.0-1.0)")

class ChatResponse(BaseModel):
    """Response from chat completion"""
    response: str = Field(..., description="LLM generated response")
    sources: Optional[List[str]] = Field(None, description="RAG source documents")
    token_usage: Optional[Dict[str, int]] = Field(None, description="Token usage statistics")
    processing_time: float = Field(..., description="Time taken to process request (seconds)")

class DocumentUploadRequest(BaseModel):
    """Request for document upload and indexing"""
    filename: str = Field(..., description="Name of the uploaded file")
    content_type: str = Field(..., description="MIME type of the file")

class DocumentUploadResponse(BaseModel):
    """Response from document upload"""
    document_id: str = Field(..., description="Unique identifier for the document")
    filename: str = Field(..., description="Name of the uploaded file")
    pages_processed: int = Field(..., description="Number of pages/chunks processed")
    status: str = Field(..., description="Processing status")
    processing_time: float = Field(..., description="Time taken to process document (seconds)")

class SearchRequest(BaseModel):
    """Request for document search"""
    query: str = Field(..., description="Search query")
    top_k: int = Field(5, description="Number of top results to return")
    threshold: float = Field(0.7, description="Similarity threshold for results")

class SearchResult(BaseModel):
    """Individual search result"""
    content: str = Field(..., description="Document content")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    similarity_score: float = Field(..., description="Similarity score (0.0-1.0)")

class SearchResponse(BaseModel):
    """Response from document search"""
    results: List[SearchResult] = Field(..., description="Search results")
    total_results: int = Field(..., description="Total number of results found")
    query_time: float = Field(..., description="Time taken to execute search (seconds)")

class HealthResponse(BaseModel):
    """Health check response"""
    status: str = Field(..., description="Service health status")
    llm_configured: bool = Field(..., description="Whether LLM API is configured")
    embedding_configured: bool = Field(..., description="Whether embedding API is configured")
    chroma_path: str = Field(..., description="ChromaDB storage path")

class ErrorResponse(BaseModel):
    """Error response"""
    error: str = Field(..., description="Error message")
    error_type: str = Field(..., description="Type of error")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp") 