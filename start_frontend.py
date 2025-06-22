#!/usr/bin/env python3
"""
Frontend startup script for Law Firm AI Assistant
"""

import subprocess
import sys
import os
from pathlib import Path

def validate_environment():
    """Validate that all required dependencies are available"""
    try:
        import streamlit
        import sqlite3
        import bcrypt
        import requests
        return True
    except ImportError as e:
        print(f"Missing dependency: {e}")
        print("Please run: pip install -r requirements.txt")
        return False

def start_frontend(port=8501):
    """Start the Streamlit frontend application"""
    
    print("Starting Law Firm AI Assistant Frontend...")
    print(f"Frontend will run on port: {port}")
    print(f"Backend API URL: http://localhost:8000")
    print("-" * 60)
    
    if not validate_environment():
        print("Environment validation failed. Please check dependencies.")
        return False
    
    try:
        # Change to the project directory
        project_root = Path(__file__).parent
        os.chdir(project_root)
        
        # Start Streamlit app
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            "frontend/app.py",
            "--server.port", str(port),
            "--server.address", "localhost",
            "--browser.gatherUsageStats", "false"
        ]
        
        subprocess.run(cmd, check=True)
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"Frontend startup failed: {e}")
        return False
    except KeyboardInterrupt:
        print("\nFrontend shutdown requested by user")
        return True
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Start Law Firm AI Assistant Frontend")
    parser.add_argument("--port", type=int, default=8501, help="Port to run frontend on (default: 8501)")
    
    args = parser.parse_args()
    
    success = start_frontend(args.port)
    sys.exit(0 if success else 1) 