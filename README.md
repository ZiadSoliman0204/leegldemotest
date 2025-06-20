# 🏛️ Law Firm AI Assistant

A production-grade AI assistant specifically designed for legal professionals. This system provides intelligent document analysis, legal research assistance, and contextual Q&A capabilities using advanced AI models while maintaining a lightweight, deployable architecture.

## 🏗️ Architecture Overview

### System Components

- **Frontend**: Streamlit-based web interface for user interaction
- **Backend**: FastAPI application with modular routing
- **Vector Database**: ChromaDB for document indexing and retrieval
- **Remote LLM**: LLaMA 3 70B hosted on CoreWeave via OpenAI-compatible API
- **Embedding Service**: OpenAI text-embedding-ada-002 for lightweight vector generation

### Data Flow

```
User Input → Streamlit UI → FastAPI Backend → RAG Search → Remote LLM → Response
                              ↓
                         ChromaDB Vector Store
```

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Access to remote LLaMA 3 70B API (CoreWeave VLLM)
- OpenAI API key for embeddings
- 2GB+ available disk space

### Installation

1. **Clone and Setup**
   ```bash
   git clone <repository-url>
   cd lawfirm_remaster
   pip install -r requirements.txt
   ```

2. **Environment Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your API credentials
   ```

3. **Required Environment Variables**
   ```env
   # Remote LLM Configuration
   LLM_API_URL=https://your-coreweave-endpoint.com/v1/chat/completions
   LLM_API_KEY=your-bearer-token-here
   LLM_MODEL_NAME=llama-3-70b

   # OpenAI for Embeddings
   OPENAI_API_KEY=your-openai-api-key-here
   EMBEDDING_MODEL=text-embedding-ada-002
   ```

### Running the Application

1. **Start Backend Server**
   ```bash
   python start_backend.py
   ```

2. **Start Frontend (New Terminal)**
   ```bash
   python start_frontend.py
   ```

3. **Access Application**
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000
   - API Documentation: http://localhost:8000/docs

## 📁 Project Structure

```
lawfirm_remaster/
├── backend/                 # FastAPI backend application
│   ├── main.py             # Application entry point
│   ├── config.py           # Configuration management
│   ├── models.py           # Pydantic data models
│   ├── routes/             # API route handlers
│   │   ├── chat.py         # Chat completion endpoints
│   │   └── documents.py    # Document management endpoints
│   └── services/           # Business logic services
│       ├── llm_client.py   # Remote LLM communication
│       ├── rag_service.py  # Vector search and indexing
│       └── document_processor.py # PDF processing and chunking
├── frontend/               # Streamlit frontend
│   └── app.py             # Main UI application
├── data/                  # Data storage (auto-created)
│   └── chroma_db/         # ChromaDB vector database
├── logs/                  # Application logs (auto-created)
├── requirements.txt       # Python dependencies
├── .env.example          # Environment configuration template
├── start_backend.py      # Backend startup script
├── start_frontend.py     # Frontend startup script
└── README.md            # This documentation
```

## 🔧 API Endpoints

### Chat Endpoints

- `POST /api/v1/chat/completions` - Process user queries with RAG
- `POST /api/v1/chat/stream` - Streaming chat responses
- `GET /api/v1/chat/models` - List available models

### Document Management

- `POST /api/v1/documents/upload` - Upload and index PDF documents
- `POST /api/v1/documents/search` - Search document chunks
- `GET /api/v1/documents/list` - List uploaded documents
- `DELETE /api/v1/documents/{id}` - Delete document and chunks
- `GET /api/v1/documents/stats` - Collection statistics

### System

- `GET /` - Basic health check
- `GET /health` - Detailed system status

## 💡 Key Features

### 🧠 Intelligent Legal Assistant
- Context-aware responses using RAG (Retrieval-Augmented Generation)
- Integration with uploaded legal documents
- Professional legal language processing

### 📄 Document Management
- PDF upload and automatic text extraction
- Intelligent document chunking for optimal retrieval
- Vector-based semantic search
- Source attribution in responses

### 🎯 Production-Ready Architecture
- Modular, scalable design
- Comprehensive error handling and logging
- Environment-based configuration
- API documentation with OpenAPI/Swagger

### 🔒 Security & Compliance
- No local model storage (reduces security footprint)
- API key based authentication
- Configurable data retention policies
- CORS protection for web interface

## 📊 Usage Examples

### Basic Chat Query
```python
# User asks: "What are the key elements of a valid contract?"
# System searches uploaded legal documents
# Returns comprehensive answer with source attribution
```

### Document-Enhanced Research
```python
# 1. Upload contract templates and legal precedents
# 2. Ask: "Based on uploaded documents, what clauses should I include in a software licensing agreement?"
# 3. Get contextual answer with specific document references
```

## 🔧 Configuration Options

### Backend Settings
- `BACKEND_HOST`: Server bind address (default: 0.0.0.0)
- `BACKEND_PORT`: Server port (default: 8000)
- `DEBUG_MODE`: Enable debug features (default: False)
- `LOG_LEVEL`: Logging verbosity (default: INFO)

### RAG Configuration
- `CHROMA_DB_PATH`: Vector database storage path
- `COLLECTION_NAME`: ChromaDB collection name
- `REQUEST_TIMEOUT`: API request timeout (seconds)

### LLM Parameters
- `MAX_TOKENS`: Maximum response length (default: 2048)
- `TEMPERATURE`: Response creativity (default: 0.7)

## 🐛 Troubleshooting

### Common Issues

1. **API Connection Errors**
   ```bash
   # Check if backend is running
   curl http://localhost:8000/health
   
   # Verify environment variables
   python -c "from backend.config import settings; print(settings.LLM_API_URL)"
   ```

2. **Document Upload Failures**
   - Ensure PDF files are not corrupted
   - Check available disk space
   - Verify OpenAI API key for embeddings

3. **Empty RAG Results**
   - Upload relevant documents first
   - Check document processing logs
   - Adjust similarity threshold in search

### Log Locations
- Backend logs: `logs/backend.log`
- Console output during startup
- ChromaDB logs in data directory

## 🚀 Deployment

### Production Deployment

1. **Environment Setup**
   ```bash
   # Use production environment variables
   export DEBUG_MODE=False
   export LOG_LEVEL=WARNING
   ```

2. **Process Management**
   ```bash
   # Use process manager like PM2 or systemd
   pm2 start start_backend.py --name lawfirm-backend
   pm2 start start_frontend.py --name lawfirm-frontend
   ```

3. **Reverse Proxy**
   - Configure nginx/Apache for production
   - Enable HTTPS for secure communication
   - Set up load balancing if needed

### Docker Deployment (Optional)
```dockerfile
# Example Dockerfile structure
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "start_backend.py"]
```

## 📈 Performance Optimization

### Backend Optimization
- Use async/await for all I/O operations
- Implement connection pooling for database
- Cache frequent API responses
- Optimize chunk sizes for your document types

### Frontend Optimization
- Enable Streamlit caching for expensive operations
- Minimize API calls with smart state management
- Implement pagination for large result sets

## 🤝 Contributing

1. Follow PEP 8 style guidelines
2. Add type hints to all functions
3. Include docstrings for all public methods
4. Write tests for new features
5. Update documentation for API changes

## 📄 License

This project is designed for legal professionals and should be used in compliance with applicable laws and regulations regarding data privacy and AI usage in legal contexts.

## 🆘 Support

For technical support or feature requests:
- Review the troubleshooting section
- Check the API documentation at `/docs`
- Examine log files for detailed error information

---

**⚖️ Built specifically for legal professionals who need intelligent, contextual AI assistance while maintaining professional standards and security requirements.** 