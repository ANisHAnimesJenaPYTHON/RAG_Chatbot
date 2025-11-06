"""Main FastAPI application"""

import json
import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse, JSONResponse, FileResponse
from google.oauth2.credentials import Credentials
from backend.auth import GoogleAuth
from backend.google_docs import GoogleDocsService
from backend.rag_pipeline import RAGPipeline
from backend.models import (
    DocumentListResponse,
    AddDocumentsRequest,
    AddDocumentsResponse,
    ChatRequest,
    ChatResponse,
    KnowledgeBaseDocumentsResponse,
    ErrorResponse
)
from backend.config import settings

app = FastAPI(title="RAG Chatbot with Google Docs", version="1.0.0")

# Serve static files
# Get project root (parent of backend directory)
frontend_path = Path(__file__).parent.parent / "frontend"

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
auth_service = GoogleAuth()
docs_service = GoogleDocsService()
rag_pipeline = RAGPipeline()

# In-memory session storage (use Redis in production)
user_sessions = {}
flow_storage = {}

# Mount static files if frontend directory exists
if frontend_path.exists():
    app.mount("/frontend", StaticFiles(directory=str(frontend_path)), name="frontend")


@app.get("/")
async def root():
    """Root endpoint - redirect to frontend"""
    frontend_file = frontend_path / "index.html"
    if frontend_file.exists():
        return FileResponse(str(frontend_file))
    return {"message": "RAG Chatbot API", "status": "running", "frontend": "Please serve frontend/index.html"}


@app.get("/auth/login")
async def login(request: Request):
    """Initiate Google OAuth login"""
    try:
        # Generate state for CSRF protection
        state = str(uuid.uuid4())
        
        # Get authorization URL
        auth_url, flow = auth_service.get_authorization_url(state=state)
        
        # Store flow in session (in production, use secure session storage)
        flow_storage[state] = flow
        
        return RedirectResponse(url=auth_url)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error initiating login: {str(e)}")


@app.get("/auth/callback")
async def callback(request: Request, code: str = None, state: str = None, error: str = None):
    """Handle OAuth callback"""
    if error:
        return JSONResponse(
            status_code=400,
            content={"error": "Authentication failed", "message": error}
        )
    
    if not code:
        raise HTTPException(status_code=400, detail="Authorization code not provided")
    
    try:
        # Retrieve flow from storage
        if state not in flow_storage:
            raise HTTPException(status_code=400, detail="Invalid state parameter")
        
        flow = flow_storage[state]
        
        # Exchange code for credentials
        credentials = auth_service.get_credentials_from_code(code, flow)
        
        # Create session
        session_id = str(uuid.uuid4())
        user_sessions[session_id] = auth_service.credentials_to_dict(credentials)
        
        # Clean up flow storage
        del flow_storage[state]
        
        # Redirect to frontend with session ID
        redirect_url = f"/frontend/index.html?session_id={session_id}"
        return RedirectResponse(url=redirect_url)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing callback: {str(e)}")


def get_credentials_from_session(session_id: str) -> Credentials:
    """Get credentials from session"""
    if session_id not in user_sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    creds_dict = user_sessions[session_id]
    return auth_service.dict_to_credentials(creds_dict)


@app.get("/api/documents")
async def get_documents(session_id: str):
    """Fetch user's Google Docs"""
    try:
        credentials = get_credentials_from_session(session_id)
        documents = docs_service.get_all_documents(credentials)
        
        return DocumentListResponse(
            documents=documents,
            success=True,
            message=f"Found {len(documents)} documents"
        )
    
    except HTTPException:
        raise
    except Exception as e:
        return DocumentListResponse(
            documents=[],
            success=False,
            message=f"Error fetching documents: {str(e)}"
        )


@app.post("/api/knowledge-base/add")
async def add_documents(request: AddDocumentsRequest, session_id: str, clear_first: bool = False):
    """Add documents to knowledge base"""
    try:
        # Option to clear existing documents first
        if clear_first:
            rag_pipeline.clear_all_documents()
        
        print(f"Adding {len(request.document_ids)} document(s) to knowledge base...")
        credentials = get_credentials_from_session(session_id)
        
        added_count = 0
        errors = []
        
        for doc_id in request.document_ids:
            try:
                print(f"Processing document {doc_id}...")
                
                # Get document content
                print(f"Fetching content for {doc_id}...")
                content = docs_service.get_document_content(doc_id, credentials)
                print(f"Content length: {len(content)} characters")
                
                if not content or len(content.strip()) == 0:
                    print(f"Warning: Document {doc_id} has no content")
                    errors.append(f"Document {doc_id} is empty")
                    continue
                
                # Get document metadata for name
                print(f"Fetching metadata for {doc_id}...")
                metadata = docs_service.get_document_metadata(doc_id, credentials)
                doc_name = metadata.get('name', f'Document {doc_id}')
                print(f"Document name: {doc_name}")
                
                # Remove existing document if present
                print(f"Removing old version of {doc_id} if exists...")
                rag_pipeline.remove_document(doc_id)
                
                # Add to knowledge base
                print(f"Adding {doc_name} to vector database...")
                rag_pipeline.add_document(doc_id, doc_name, content)
                added_count += 1
                print(f"Successfully added {doc_name}!")
                
            except Exception as e:
                # Log error but continue with other documents
                error_msg = f"Error processing document {doc_id}: {str(e)}"
                print(error_msg)
                import traceback
                traceback.print_exc()
                errors.append(error_msg)
                continue
        
        if added_count > 0:
            return AddDocumentsResponse(
                success=True,
                message=f"Successfully added {added_count} document(s) to knowledge base" + (f". Errors: {len(errors)}" if errors else ""),
                added_count=added_count
            )
        else:
            return AddDocumentsResponse(
                success=False,
                message=f"Failed to add documents. Errors: {'; '.join(errors)}",
                added_count=0
            )
    
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        return AddDocumentsResponse(
            success=False,
            message=f"Error adding documents: {str(e)}",
            added_count=0
        )


@app.get("/api/knowledge-base/documents")
async def get_knowledge_base_documents():
    """Get list of documents in knowledge base"""
    try:
        documents = rag_pipeline.get_knowledge_base_documents()
        
        return KnowledgeBaseDocumentsResponse(
            documents=documents,
            success=True
        )
    
    except Exception as e:
        return KnowledgeBaseDocumentsResponse(
            documents=[],
            success=False
        )


@app.delete("/api/knowledge-base/clear")
async def clear_knowledge_base():
    """Clear all documents from knowledge base"""
    try:
        rag_pipeline.clear_all_documents()
        return {"success": True, "message": "Knowledge base cleared successfully"}
    except Exception as e:
        return {"success": False, "message": f"Error clearing knowledge base: {str(e)}"}


@app.post("/api/chat")
async def chat(request: ChatRequest, session_id: str):
    """Query the chatbot"""
    try:
        # Search in knowledge base
        retrieved_docs, scores = rag_pipeline.search(request.query, top_k=5)
        
        # Determine if answer was found in documents
        # Use a threshold for cosine similarity/distance
        found_in_documents = False
        relevant_contexts = []
        
        if retrieved_docs:
            # Use a more lenient threshold - accept results with distance < 1.0
            # (ChromaDB uses cosine distance, lower is better)
            for doc, score in zip(retrieved_docs, scores):
                if score < 1.0:  # More lenient threshold
                    found_in_documents = True
                    relevant_contexts.append(doc)
        
        # If we have any results, consider it found (even if threshold is high)
        if retrieved_docs and not found_in_documents:
            found_in_documents = True
            relevant_contexts = retrieved_docs[:3]  # Use top 3 results
        
        # Generate response
        response_text = rag_pipeline.generate_response(
            request.query,
            relevant_contexts,
            found_in_documents
        )
        
        # Format sources (deduplicate by document name)
        sources_dict = {}
        for ctx in relevant_contexts:
            metadata = ctx.get('metadata', {})
            doc_name = metadata.get('document_name', 'Unknown')
            doc_id = metadata.get('document_id', '')
            
            # Only add once per document, keep the highest relevance
            if doc_name not in sources_dict:
                sources_dict[doc_name] = {
                    'document_name': doc_name,
                    'document_id': doc_id,
                    'relevance_score': 1 - ctx.get('distance', 1.0)
                }
            else:
                # Update if this one has higher relevance
                current_score = sources_dict[doc_name]['relevance_score']
                new_score = 1 - ctx.get('distance', 1.0)
                if new_score > current_score:
                    sources_dict[doc_name]['relevance_score'] = new_score
        
        sources = list(sources_dict.values())
        
        # Generate or use conversation ID
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        return ChatResponse(
            response=response_text,
            sources=sources,
            found_in_documents=found_in_documents,
            conversation_id=conversation_id
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {str(e)}")


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

