#!/usr/bin/env python3
"""
Startup script for Law Firm AI Assistant Backend
Runs the FastAPI server with proper configuration
"""

import uvicorn
import os
import sys
from dotenv import load_dotenv
from loguru import logger

# Load environment variables
load_dotenv()

def setup_logging():
    """Configure logging for the application"""
    log_level = os.getenv("LOG_LEVEL", "INFO")
    
    # Remove default logger
    logger.remove()
    
    # Add console logger with custom format
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level
    )
    
    # Add file logger
    logger.add(
        "logs/backend.log",
        rotation="1 day",
        retention="30 days",
        level=log_level,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
    )

def validate_environment():
    """Validate that required environment variables are set"""
    required_vars = [
        "LLM_API_URL",
        "LLM_API_KEY",
        "OPENAI_API_KEY"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file and ensure all required variables are set.")
        sys.exit(1)
    
    logger.info("Environment validation passed")

def create_directories():
    """Create necessary directories"""
    directories = [
        "logs",
        "data",
        os.getenv("CHROMA_DB_PATH", "./data/chroma_db")
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        logger.info(f"Ensured directory exists: {directory}")

def main():
    """Main function to start the backend server"""
    # Setup
    setup_logging()
    logger.info("Starting Law Firm AI Assistant Backend")
    
    # Validate environment
    validate_environment()
    
    # Create directories
    create_directories()
    
    # Get configuration
    host = os.getenv("BACKEND_HOST", "0.0.0.0")
    port = int(os.getenv("BACKEND_PORT", "8000"))
    debug_mode = os.getenv("DEBUG_MODE", "False").lower() == "true"
    
    logger.info(f"Server configuration: {host}:{port} (debug={debug_mode})")
    
    # Start the server
    try:
        uvicorn.run(
            "backend.main:app",
            host=host,
            port=port,
            reload=debug_mode,
            log_level="info" if not debug_mode else "debug",
            access_log=True
        )
    except KeyboardInterrupt:
        logger.info("Server shutdown requested by user")
    except Exception as e:
        logger.error(f"Server startup failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 