"""
RAG (Retrieval Augmented Generation) Service for Law Firm AI Assistant
Uses local embeddings and ChromaDB for document retrieval
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Any, Optional
import uuid
import os
import tempfile
import logging
from pathlib import Path

from .document_processor import LocalDocumentProcessor

logger = logging.getLogger(__name__)

class LocalRAGService:
    """RAG service using local embeddings and ChromaDB"""
    
    def __init__(self, chroma_db_path: str = "data/chroma_db"):
        """
        Initialize RAG service with local components
        
        Args:
            chroma_db_path: Path to ChromaDB storage
        """
        self.chroma_db_path = chroma_db_path
        self.document_processor = LocalDocumentProcessor()
        self.collection_name = "law_firm_documents"
        
        # Initialize ChromaDB
        self._initialize_chroma_client()
        
        logger.info("LocalRAGService initialized with local embeddings")
    
    def _initialize_chroma_client(self):
        """Initialize ChromaDB client and collection"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(self.chroma_db_path, exist_ok=True)
            
            # Initialize ChromaDB client
            self.chroma_client = chromadb.PersistentClient(
                path=self.chroma_db_path,
                settings=Settings(
                    allow_reset=True,
                    anonymized_telemetry=False
                )
            )
            
            # Get or create collection
            try:
                self.collection = self.chroma_client.get_collection(
                    name=self.collection_name
                )
                logger.info(f"Using existing collection: {self.collection_name}")
            except ValueError:
                # Collection doesn't exist, create it
                self.collection = self.chroma_client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Law firm documents with local embeddings"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
                
        except Exception as error:
            logger.error(f"Failed to initialize ChromaDB: {error}")
            raise
    
    def upload_document(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """
        Process and upload a document to the vector database
        
        Args:
            file_content: Raw file content
            filename: Original filename
            
        Returns:
            Upload result dictionary
        """
        try:
            # Validate file type
            file_extension = Path(filename).suffix.lower()
            if file_extension not in self.document_processor.supported_formats:
                raise ValueError(f"Unsupported file format: {file_extension}. "
                               f"Supported formats: {', '.join(self.document_processor.supported_formats)}")
            
            # Save file temporarily for processing
            with tempfile.NamedTemporaryFile(
                delete=False, 
                suffix=file_extension,
                prefix="law_firm_doc_"
            ) as temp_file:
                temp_file.write(file_content)
                temp_file_path = temp_file.name
            
            try:
                # Process document
                logger.info(f"Processing document: {filename}")
                processing_result = self.document_processor.process_document(
                    file_path=temp_file_path,
                    filename=filename
                )
                
                # Store in ChromaDB
                self._store_document_chunks(processing_result)
                
                logger.info(f"Successfully uploaded {filename} with {len(processing_result['chunks'])} chunks")
                
                return {
                    "document_id": processing_result["document_id"],
                    "filename": filename,
                    "pages_processed": processing_result["pages_processed"],
                    "total_chunks": len(processing_result["chunks"]),
                    "file_type": file_extension,
                    "processing_method": "local"
                }
                
            finally:
                # Clean up temporary file
                try:
                    os.unlink(temp_file_path)
                except Exception as cleanup_error:
                    logger.warning(f"Failed to clean up temp file: {cleanup_error}")
                
        except Exception as error:
            logger.error(f"Error uploading document {filename}: {error}")
            raise ValueError(f"Failed to upload document: {str(error)}")
    
    def _store_document_chunks(self, processing_result: Dict[str, Any]):
        """Store processed document chunks in ChromaDB"""
        try:
            chunks = processing_result["chunks"]
            
            # Prepare data for ChromaDB
            ids = []
            documents = []
            embeddings = []
            metadatas = []
            
            for chunk in chunks:
                # Create unique ID for each chunk
                chunk_id = f"{chunk['metadata']['document_id']}_chunk_{chunk['metadata']['chunk_index']}"
                
                ids.append(chunk_id)
                documents.append(chunk["text"])
                embeddings.append(chunk["embedding"])
                metadatas.append(chunk["metadata"])
            
            # Add to ChromaDB collection
            self.collection.add(
                ids=ids,
                documents=documents,
                embeddings=embeddings,
                metadatas=metadatas
            )
            
            logger.info(f"Stored {len(chunks)} chunks in ChromaDB")
            
        except Exception as error:
            logger.error(f"Error storing chunks in ChromaDB: {error}")
            raise
    
    def search_documents(self, query: str, n_results: int = 5, selected_document_ids: Optional[List[str]] = None) -> List[Dict[str, Any]]:
        """
        Search for relevant document chunks using local embeddings
        
        Args:
            query: Search query
            n_results: Number of results to return
            selected_document_ids: Optional list of document IDs to filter by
            
        Returns:
            List of relevant document chunks
        """
        try:
            if not query.strip():
                return []
            
            # Generate embedding for query using local method
            query_embedding = self.document_processor._generate_local_embedding(query)
            
            # Prepare where clause for document filtering
            where_clause = None
            if selected_document_ids:
                if len(selected_document_ids) == 1:
                    where_clause = {"document_id": selected_document_ids[0]}
                else:
                    where_clause = {"document_id": {"$in": selected_document_ids}}
            
            # Search in ChromaDB with optional filtering
            search_params = {
                "query_embeddings": [query_embedding],
                "n_results": min(n_results, 10)  # Cap at 10 results
            }
            
            if where_clause:
                search_params["where"] = where_clause
            
            results = self.collection.query(**search_params)
            
            # Format results
            formatted_results = []
            
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    result = {
                        'content': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i] if results['metadatas'] else {},
                        'distance': results['distances'][0][i] if results['distances'] else 0.0,
                        'similarity': 1.0 - results['distances'][0][i] if results['distances'] else 1.0
                    }
                    formatted_results.append(result)
            
            search_context = f"all documents" if not selected_document_ids else f"selected documents: {', '.join(selected_document_ids)}"
            logger.info(f"Found {len(formatted_results)} relevant chunks for query in {search_context}")
            return formatted_results
            
        except Exception as error:
            logger.error(f"Error searching documents: {error}")
            return []
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document and all its chunks from the vector database
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get all chunks for this document
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if not results['ids']:
                logger.warning(f"No chunks found for document ID: {document_id}")
                return False
            
            # Delete all chunks
            self.collection.delete(ids=results['ids'])
            
            logger.info(f"Deleted document {document_id} and {len(results['ids'])} chunks")
            return True
            
        except Exception as error:
            logger.error(f"Error deleting document {document_id}: {error}")
            return False
    
    def list_documents(self) -> List[Dict[str, Any]]:
        """
        List all documents in the vector database
        
        Returns:
            List of document metadata
        """
        try:
            # Get all documents
            results = self.collection.get()
            
            # Group by document_id
            documents = {}
            
            for i, metadata in enumerate(results['metadatas']):
                doc_id = metadata.get('document_id', 'unknown')
                
                if doc_id not in documents:
                    documents[doc_id] = {
                        'document_id': doc_id,
                        'filename': metadata.get('filename', 'unknown'),
                        'file_type': metadata.get('file_type', 'unknown'),
                        'chunk_count': 0
                    }
                
                documents[doc_id]['chunk_count'] += 1
            
            document_list = list(documents.values())
            logger.info(f"Found {len(document_list)} documents in database")
            
            return document_list
            
        except Exception as error:
            logger.error(f"Error listing documents: {error}")
            return []
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the document collection
        
        Returns:
            Collection statistics
        """
        try:
            # Get collection info
            collection_count = self.collection.count()
            
            # Get document list for additional stats
            documents = self.list_documents()
            
            stats = {
                'total_chunks': collection_count,
                'total_documents': len(documents),
                'collection_name': self.collection_name,
                'storage_path': self.chroma_db_path,
                'embedding_method': 'local_tfidf_hash',
                'supported_formats': self.document_processor.supported_formats
            }
            
            # Add file type breakdown
            file_types = {}
            for doc in documents:
                file_type = doc.get('file_type', 'unknown')
                file_types[file_type] = file_types.get(file_type, 0) + 1
            
            stats['file_type_breakdown'] = file_types
            
            return stats
            
        except Exception as error:
            logger.error(f"Error getting collection stats: {error}")
            return {
                'total_chunks': 0,
                'total_documents': 0,
                'error': str(error)
            }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the RAG service
        
        Returns:
            Health status dictionary
        """
        try:
            # Test collection access
            count = self.collection.count()
            
            # Test document processor
            test_embedding = self.document_processor._generate_local_embedding("test")
            
            return {
                'status': 'healthy',
                'chroma_db_accessible': True,
                'document_count': count,
                'embedding_service': 'local',
                'embedding_dimension': len(test_embedding),
                'supported_formats': self.document_processor.supported_formats
            }
            
        except Exception as error:
            logger.error(f"RAG service health check failed: {error}")
            return {
                'status': 'unhealthy',
                'error': str(error),
                'chroma_db_accessible': False
            } 