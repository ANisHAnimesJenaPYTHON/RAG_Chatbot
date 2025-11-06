"""Google Docs API integration"""

from typing import List, Dict
from googleapiclient.errors import HttpError
from backend.auth import GoogleAuth
from backend.models import DocumentInfo


class GoogleDocsService:
    """Service for interacting with Google Docs API"""
    
    def __init__(self):
        self.auth = GoogleAuth()
    
    def get_all_documents(self, credentials) -> List[DocumentInfo]:
        """Fetch all Google Docs for the authenticated user"""
        try:
            drive_service = self.auth.get_authenticated_service(credentials)
            
            # Fetch Google Docs visible to the user, including:
            # - User's own files
            # - Files shared with the user (sharedWithMe)
            # - Files in shared drives (if any)
            queries = [
                "mimeType='application/vnd.google-apps.document' and trashed=false",
                "mimeType='application/vnd.google-apps.document' and trashed=false and sharedWithMe"
            ]
            fields = "nextPageToken, files(id, name, mimeType, modifiedTime, webViewLink)"
            seen_ids = {}
            
            for q in queries:
                page_token = None
                while True:
                    resp = drive_service.files().list(
                        q=q,
                        fields=fields,
                        orderBy="modifiedTime desc",
                        includeItemsFromAllDrives=True,
                        supportsAllDrives=True,
                        corpora="allDrives",
                        pageToken=page_token
                    ).execute()
                    for f in resp.get('files', []):
                        seen_ids[f['id']] = f
                    page_token = resp.get('nextPageToken')
                    if not page_token:
                        break
            
            documents: List[DocumentInfo] = []
            for file in seen_ids.values():
                documents.append(DocumentInfo(
                    id=file['id'],
                    name=file['name'],
                    mimeType=file['mimeType'],
                    modifiedTime=file.get('modifiedTime', ''),
                    webViewLink=file.get('webViewLink')
                ))
            
            # Sort by modified time desc (already ordered, but ensure after merge)
            documents.sort(key=lambda d: d.modifiedTime or "", reverse=True)
            return documents
            
        except HttpError as error:
            raise Exception(f"Error fetching documents: {error}")
    
    def get_document_content(self, document_id: str, credentials) -> str:
        """Extract text content from a Google Doc"""
        try:
            docs_service = self.auth.get_docs_service(credentials)
            
            document = docs_service.documents().get(documentId=document_id).execute()
            
            # Extract text from all elements
            text_content = []
            
            def extract_text(elements):
                """Recursively extract text from document elements"""
                for element in elements:
                    if 'paragraph' in element:
                        para = element['paragraph']
                        if 'elements' in para:
                            for elem in para['elements']:
                                if 'textRun' in elem:
                                    text_content.append(elem['textRun'].get('content', ''))
                    if 'table' in element:
                        table = element['table']
                        if 'tableRows' in table:
                            for row in table['tableRows']:
                                if 'tableCells' in row:
                                    for cell in row['tableCells']:
                                        if 'content' in cell:
                                            extract_text(cell['content'])
            
            if 'body' in document and 'content' in document['body']:
                extract_text(document['body']['content'])
            
            full_text = ''.join(text_content).strip()
            return full_text
            
        except HttpError as error:
            raise Exception(f"Error fetching document content: {error}")
    
    def get_document_metadata(self, document_id: str, credentials) -> Dict:
        """Get metadata for a specific document"""
        try:
            drive_service = self.auth.get_authenticated_service(credentials)
            
            file = drive_service.files().get(
                fileId=document_id,
                fields="id, name, mimeType, modifiedTime, webViewLink"
            ).execute()
            
            return file
            
        except HttpError as error:
            raise Exception(f"Error fetching document metadata: {error}")

