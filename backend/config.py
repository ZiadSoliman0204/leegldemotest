"""
Configuration management for Law Firm AI Assistant Backend
Handles environment variables and application settings
"""

import os
from typing import Optional
from pydantic import BaseModel, validator
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Settings(BaseSettings):
    """Application settings with validation"""
    
    # Remote LLM Configuration
    LLM_API_URL: str = os.getenv("LLM_API_URL", "")
    LLM_API_KEY: str = os.getenv("LLM_API_KEY", "")
    LLM_MODEL_NAME: str = os.getenv("LLM_MODEL_NAME", "llama-3-70b")
    
    # OpenAI Configuration for Embeddings
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
    
    # ChromaDB Configuration
    CHROMA_DB_PATH: str = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
    COLLECTION_NAME: str = os.getenv("COLLECTION_NAME", "legal_documents")
    
    # FastAPI Configuration
    BACKEND_HOST: str = os.getenv("BACKEND_HOST", "0.0.0.0")
    BACKEND_PORT: int = int(os.getenv("BACKEND_PORT", "8000"))
    DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    # Streamlit Configuration
    FRONTEND_PORT: int = int(os.getenv("FRONTEND_PORT", "8501"))
    
    # Logging Configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Default generation parameters
    DEFAULT_MAX_TOKENS: int = int(os.getenv("DEFAULT_MAX_TOKENS", "2048"))
    DEFAULT_TEMPERATURE: float = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
    DEFAULT_TOP_P: float = float(os.getenv("DEFAULT_TOP_P", "0.9"))
    
    # Legacy parameter names for backward compatibility
    MAX_TOKENS: int = int(os.getenv("MAX_TOKENS", os.getenv("DEFAULT_MAX_TOKENS", "2048")))
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", os.getenv("DEFAULT_TEMPERATURE", "0.7")))
    
    # Request timeout settings
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "60"))
    
    # Document processing settings
    MAX_CHUNK_SIZE: int = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
    CHUNK_OVERLAP: int = int(os.getenv("CHUNK_OVERLAP", "200"))
    MAX_SEARCH_RESULTS: int = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
    
    # Security settings
    CORS_ORIGINS: list = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
        "http://localhost:3000",
        "http://127.0.0.1:3000"
    ]
    
    @validator('LLM_API_URL')
    def validate_llm_url(cls, v):
        """Validate that LLM API URL is provided"""
        if not v:
            raise ValueError("LLM_API_URL must be provided")
        return v
    
    @validator('LLM_API_KEY')
    def validate_llm_key(cls, v):
        """Validate that LLM API key is provided"""
        if not v:
            raise ValueError("LLM_API_KEY must be provided")
        return v
    
    @validator('OPENAI_API_KEY')
    def validate_openai_key(cls, v):
        """Validate that OpenAI API key is provided"""
        if not v:
            raise ValueError("OPENAI_API_KEY must be provided")
        return v
    
    @validator('BACKEND_PORT', 'FRONTEND_PORT')
    def validate_ports(cls, v):
        """Validate port numbers are in valid range"""
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v
    
    @validator('DEFAULT_TEMPERATURE', 'DEFAULT_TOP_P')
    def validate_float_range(cls, v):
        """Validate float parameters are in valid range"""
        if not 0.0 <= v <= 1.0:
            raise ValueError("Temperature and top_p must be between 0.0 and 1.0")
        return v
    
    class Config:
        """Pydantic configuration"""
        env_file = ".env"
        case_sensitive = True

# Create settings instance
try:
    settings = Settings()
except Exception as e:
    # If validation fails, create a more permissive version for startup
    print(f"Warning: Configuration validation failed: {e}")
    print("Using fallback configuration - some features may not work correctly")
    
    class FallbackSettings:
        """Fallback settings when validation fails"""
        LLM_API_URL = os.getenv("LLM_API_URL", "http://localhost:11434/v1/chat/completions")
        LLM_API_KEY = os.getenv("LLM_API_KEY", "fallback-key")
        LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "llama-3-70b")
        
        OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "fallback-key")
        EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-ada-002")
        
        CHROMA_DB_PATH = os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
        COLLECTION_NAME = os.getenv("COLLECTION_NAME", "legal_documents")
        
        BACKEND_HOST = os.getenv("BACKEND_HOST", "0.0.0.0")
        BACKEND_PORT = int(os.getenv("BACKEND_PORT", "8000"))
        DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() == "true"
        
        FRONTEND_PORT = int(os.getenv("FRONTEND_PORT", "8501"))
        LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
        
        DEFAULT_MAX_TOKENS = int(os.getenv("DEFAULT_MAX_TOKENS", "2048"))
        DEFAULT_TEMPERATURE = float(os.getenv("DEFAULT_TEMPERATURE", "0.7"))
        DEFAULT_TOP_P = float(os.getenv("DEFAULT_TOP_P", "0.9"))
        
        # Legacy parameter names for backward compatibility
        MAX_TOKENS = int(os.getenv("MAX_TOKENS", os.getenv("DEFAULT_MAX_TOKENS", "2048")))
        TEMPERATURE = float(os.getenv("TEMPERATURE", os.getenv("DEFAULT_TEMPERATURE", "0.7")))
        
        # Request timeout settings
        REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
        
        MAX_CHUNK_SIZE = int(os.getenv("MAX_CHUNK_SIZE", "1000"))
        CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "200"))
        MAX_SEARCH_RESULTS = int(os.getenv("MAX_SEARCH_RESULTS", "5"))
        
        CORS_ORIGINS = [
            "http://localhost:8501",
            "http://127.0.0.1:8501",
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]
    
    settings = FallbackSettings() 