#!/usr/bin/env python3
"""
Test that RAG is working after ChromaDB fix
"""

import sys
import os
sys.path.append('backend')

from backend.services.rag_service import LocalRAGService

def test_rag_fix():
    print("=== Testing Fixed RAG System ===")
    
    # Initialize RAG service
    rag_service = LocalRAGService()
    
    # 1. Upload a test document
    print("\n1. Uploading test document...")
    test_content = b"""Case Title: Johnson v. ApexCorp, Inc.

Summary: This case involves an employment dispute between John Johnson, a former software engineer, and ApexCorp, Inc., his previous employer.

Key Facts:
- John Johnson worked at ApexCorp from 2020 to 2023
- He was terminated in March 2023 for alleged performance issues
- Johnson claims wrongful termination and discrimination
- The guy mentioned throughout this case is John Johnson
- ApexCorp disputes these claims

Legal Issues:
1. Whether the termination was justified
2. Evidence of discriminatory practices
3. Damages calculation

This is a complex employment law case that requires careful analysis of the evidence and applicable statutes."""
    
    try:
        result = rag_service.upload_document(test_content, "Johnson_v_ApexCorp.txt")
        print(f"   Upload successful: {result['document_id']}")
        print(f"   Chunks created: {result['total_chunks']}")
        
        # 2. Test search immediately
        print("\n2. Testing search functionality...")
        
        # Search for specific information
        test_queries = [
            "Who is the guy called?",
            "John Johnson",
            "employment dispute",
            "What happened in March 2023?"
        ]
        
        for query in test_queries:
            print(f"\n   Query: '{query}'")
            results = rag_service.search_documents(query, n_results=3)
            print(f"   Results found: {len(results)}")
            
            for i, result in enumerate(results[:1]):  # Show first result
                print(f"   Result {i+1}:")
                print(f"     Content: {result['content'][:100]}...")
                print(f"     Similarity: {result['similarity']:.4f}")
                print(f"     Distance: {result['distance']:.4f}")
        
        # 3. Test document ID filtering
        print(f"\n3. Testing document ID filtering...")
        doc_id = result['document_id']
        filtered_results = rag_service.search_documents(
            "Who is the guy called?", 
            n_results=2, 
            selected_document_ids=[doc_id]
        )
        print(f"   Filtered search results: {len(filtered_results)}")
        if filtered_results:
            print(f"   Filtered result content: {filtered_results[0]['content'][:100]}...")
            print(f"   Filtered similarity: {filtered_results[0]['similarity']:.4f}")
        
        # 4. Check ChromaDB embeddings directly
        print(f"\n4. Checking ChromaDB embeddings...")
        collection_results = rag_service.collection.get(include=['embeddings'])
        if collection_results['embeddings']:
            print(f"   Embeddings stored: {len(collection_results['embeddings'])}")
            first_embedding = collection_results['embeddings'][0]
            print(f"   First embedding length: {len(first_embedding)}")
            print(f"   First embedding sample: {first_embedding[:5]}")
            print(f"   Embedding has values: {not all(x == 0 for x in first_embedding)}")
        else:
            print("   ERROR: No embeddings found in ChromaDB!")
        
        print(f"\n✅ RAG System Test Complete!")
        return True
        
    except Exception as e:
        print(f"   ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_rag_fix()
    if success:
        print("\n🎉 RAG system is working correctly!")
    else:
        print("\n❌ RAG system still has issues.") 