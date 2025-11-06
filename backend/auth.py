"""Google OAuth 2.0 authentication handling"""

import os
import json
from typing import Tuple
from fastapi import HTTPException
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from backend.config import settings


class GoogleAuth:
    """Handle Google OAuth authentication"""
    
    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.redirect_uri
        self.scopes = settings.google_scopes
        
    def get_authorization_url(self, state: str = None) -> Tuple[str, Flow]:
        """Get Google OAuth authorization URL"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.scopes,
            redirect_uri=self.redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            state=state,
            prompt='consent'
        )
        
        return auth_url, flow
    
    def get_credentials_from_code(self, code: str, flow: Flow) -> Credentials:
        """Exchange authorization code for credentials"""
        flow.fetch_token(code=code)
        return flow.credentials
    
    def credentials_to_dict(self, credentials: Credentials) -> dict:
        """Convert credentials to dictionary for storage"""
        return {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
    
    def dict_to_credentials(self, creds_dict: dict) -> Credentials:
        """Convert dictionary to credentials object"""
        return Credentials(**creds_dict)
    
    def refresh_credentials_if_needed(self, credentials: Credentials) -> Credentials:
        """Refresh credentials if they are expired"""
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(Request())
        return credentials
    
    def get_authenticated_service(self, credentials: Credentials):
        """Get authenticated Google Drive service"""
        credentials = self.refresh_credentials_if_needed(credentials)
        return build('drive', 'v3', credentials=credentials)
    
    def get_docs_service(self, credentials: Credentials):
        """Get authenticated Google Docs service"""
        credentials = self.refresh_credentials_if_needed(credentials)
        return build('docs', 'v1', credentials=credentials)

