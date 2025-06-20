"""
Main FastAPI application for Law Firm AI Assistant
Provides routing to remote LLM and document management capabilities
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
from loguru import logger

from .routes import chat, documents
from .config import settings

# Load environment variables
load_dotenv()

# Initialize FastAPI app
app = FastAPI(
    title="Law Firm AI Assistant API",
    description="Production-grade AI assistant for legal professionals",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG_MODE else None,
    redoc_url="/redoc" if settings.DEBUG_MODE else None
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],  # Streamlit frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat.router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(documents.router, prefix="/api/v1/documents", tags=["documents"])

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Starting Law Firm AI Assistant API")
    logger.info(f"LLM API URL: {settings.LLM_API_URL}")
    logger.info(f"ChromaDB Path: {settings.CHROMA_DB_PATH}")

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Law Firm AI Assistant API",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Detailed health check endpoint"""
    return {
        "status": "healthy",
        "llm_configured": bool(settings.LLM_API_URL and settings.LLM_API_KEY),
        "embedding_service": "local",
        "chroma_path": settings.CHROMA_DB_PATH
    } 