#!/usr/bin/env python3
"""
Startup script for Law Firm AI Assistant Frontend
Runs the Streamlit application with proper configuration
"""

import subprocess
import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    """Main function to start the Streamlit frontend"""
    print("🚀 Starting Law Firm AI Assistant Frontend...")
    
    # Get configuration
    port = os.getenv("FRONTEND_PORT", "8501")
    backend_url = f"http://localhost:{os.getenv('BACKEND_PORT', '8000')}"
    
    # Set environment variables for the frontend
    env = os.environ.copy()
    env["API_BASE_URL"] = backend_url
    
    print(f"📊 Frontend will run on port: {port}")
    print(f"🔗 Backend API URL: {backend_url}")
    print("💡 Make sure the backend is running before using the application")
    print("-" * 60)
    
    try:
        # Start Streamlit
        cmd = [
            sys.executable, "-m", "streamlit", "run", 
            "frontend/app.py",
            "--server.port", port,
            "--server.address", "0.0.0.0",
            "--browser.gatherUsageStats", "false"
        ]
        
        subprocess.run(cmd, env=env, check=True)
        
    except KeyboardInterrupt:
        print("\n👋 Frontend shutdown requested by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Frontend startup failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 