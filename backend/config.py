"""Configuration and environment variables"""

import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseSettings):
    """Application settings"""
    
    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/auth/callback"
    
    # OpenAI
    openai_api_key: str = ""
    
    # Session
    secret_key: str = "default-secret-key-change-in-production"
    
    # Embeddings
    use_local_embeddings: bool = True
    
    # ChromaDB
    chroma_db_path: str = "./chroma_db"
    
    # Scopes for Google APIs
    google_scopes: list = [
        'https://www.googleapis.com/auth/drive.readonly',
        'https://www.googleapis.com/auth/documents.readonly'
    ]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

