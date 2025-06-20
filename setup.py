#!/usr/bin/env python3
"""
Setup script for Law Firm AI Assistant
Validates environment and prepares the application for first run
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """Check if Python version is compatible"""
    if sys.version_info < (3, 8):
        print("❌ Error: Python 3.8 or higher is required")
        print(f"Current version: {sys.version}")
        return False
    print(f"✅ Python version: {sys.version.split()[0]}")
    return True

def install_dependencies():
    """Install required Python packages"""
    print("📦 Installing dependencies...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def create_directories():
    """Create necessary directories"""
    directories = [
        "data",
        "data/chroma_db", 
        "logs"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created directory: {directory}")

def check_env_file():
    """Check if .env file exists and has required variables"""
    env_file = Path(".env")
    env_example = Path(".env.example")
    
    if not env_file.exists():
        if env_example.exists():
            print("⚠️  .env file not found. Creating from template...")
            env_file.write_text(env_example.read_text())
            print("✅ .env file created from template")
            print("🔧 Please edit .env file with your API credentials before running the application")
        else:
            print("❌ Neither .env nor .env.example found")
            return False
    else:
        print("✅ .env file exists")
    
    # Check for required variables
    required_vars = ["LLM_API_URL", "LLM_API_KEY", "OPENAI_API_KEY"]
    missing_vars = []
    
    if env_file.exists():
        env_content = env_file.read_text()
        for var in required_vars:
            if f"{var}=" not in env_content or f"{var}=your-" in env_content:
                missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️  Please configure these variables in .env: {', '.join(missing_vars)}")
        return False
    
    return True

def validate_setup():
    """Validate that the setup is complete and functional"""
    print("\n🔍 Validating setup...")
    
    # Check if we can import main modules
    try:
        from backend.config import settings
        print("✅ Backend configuration loaded")
    except ImportError as e:
        print(f"❌ Backend import error: {e}")
        return False
    
    try:
        import streamlit
        print("✅ Streamlit available")
    except ImportError:
        print("❌ Streamlit not available")
        return False
    
    try:
        import chromadb
        print("✅ ChromaDB available")
    except ImportError:
        print("❌ ChromaDB not available")
        return False
    
    try:
        import openai
        print("✅ OpenAI client available")
    except ImportError:
        print("❌ OpenAI client not available")
        return False
    
    return True

def main():
    """Main setup function"""
    print("🏛️ Law Firm AI Assistant - Setup")
    print("=" * 50)
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    # Install dependencies
    if not install_dependencies():
        sys.exit(1)
    
    # Create directories
    create_directories()
    
    # Check environment configuration
    env_ok = check_env_file()
    
    # Validate setup
    if validate_setup():
        print("\n🎉 Setup completed successfully!")
        print("\nNext steps:")
        if not env_ok:
            print("1. 🔧 Configure your API keys in the .env file")
            print("2. 🚀 Run: python start_backend.py")
            print("3. 🌐 Run: python start_frontend.py (in another terminal)")
        else:
            print("1. 🚀 Run: python start_backend.py")
            print("2. 🌐 Run: python start_frontend.py (in another terminal)")
        print("4. 🌍 Open: http://localhost:8501")
    else:
        print("\n❌ Setup validation failed. Please check the errors above.")
        sys.exit(1)

if __name__ == "__main__":
    main() 