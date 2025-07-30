#!/usr/bin/env python3
"""
Fix ChromaDB collection by clearing and recreating it
"""

import sys
import os
import shutil
sys.path.append('backend')

from backend.services.rag_service import LocalRAGService

def fix_chromadb():
    print("=== Fixing ChromaDB Collection ===")
    
    try:
        # 1. Delete the existing ChromaDB data
        chroma_path = "data/chroma_db"
        if os.path.exists(chroma_path):
            print(f"Deleting existing ChromaDB data at {chroma_path}")
            shutil.rmtree(chroma_path)
        
        # 2. Initialize fresh RAG service (this will create new collection)
        print("Initializing fresh RAG service...")
        rag_service = LocalRAGService()
        
        # 3. Check the new collection
        stats = rag_service.get_collection_stats()
        print(f"New collection stats: {stats}")
        
        print("\nChromaDB collection has been reset!")
        print("Please re-upload your documents to rebuild the embeddings index.")
        
    except Exception as e:
        print(f"Error fixing ChromaDB: {e}")

if __name__ == "__main__":
    fix_chromadb() 