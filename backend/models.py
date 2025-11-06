"""Pydantic models for request/response validation"""

from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class DocumentInfo(BaseModel):
    """Google Doc information"""
    id: str
    name: str
    mimeType: str
    modifiedTime: str
    webViewLink: Optional[str] = None


class DocumentListResponse(BaseModel):
    """Response model for document list"""
    documents: List[DocumentInfo]
    success: bool
    message: Optional[str] = None


class AddDocumentsRequest(BaseModel):
    """Request model for adding documents to knowledge base"""
    document_ids: List[str]


class AddDocumentsResponse(BaseModel):
    """Response model for adding documents"""
    success: bool
    message: str
    added_count: int


class ChatRequest(BaseModel):
    """Request model for chatbot queries"""
    query: str
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response model for chatbot responses"""
    response: str
    sources: List[Dict[str, Any]]
    found_in_documents: bool
    conversation_id: str


class KnowledgeBaseDocumentsResponse(BaseModel):
    """Response model for knowledge base documents"""
    documents: List[Dict[str, str]]
    success: bool


class ErrorResponse(BaseModel):
    """Error response model"""
    success: bool = False
    error: str
    message: Optional[str] = None

