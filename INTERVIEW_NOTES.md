# RAG Chatbot (Google Docs) — Simple Interview Notes

## 1) End-to-end: How the system works
- You open the web page and click “Sign in with Google”.
- The app asks Google for permission to read your Docs (read-only).
- After you pick Docs and click “Add to Knowledge Base”, the backend:
  1) Downloads the text of those Docs
  2) Splits the text into small pieces (chunks)
  3) Turns each chunk into numbers (embeddings)
  4) Stores them in a fast search database (ChromaDB)
- When you ask a question, the backend:
  1) Turns your question into numbers (embedding)
  2) Finds the most similar chunks
  3) Uses those chunks to build an answer
  4) If it can’t find anything useful, it says so and still tries to help from general knowledge (fallback)

## 2) How frontend and backend talk
- Frontend: simple HTML/CSS/JS
- Backend: FastAPI (Python)
- They communicate using HTTP (JSON):
  - GET /auth/login → start Google login
  - GET /api/documents?session_id=… → list Docs
  - POST /api/knowledge-base/add?session_id=… → add Docs to KB
  - GET /api/knowledge-base/documents → list Docs in KB
  - POST /api/chat?session_id=… → ask a question

## 3) OAuth 2.0 flow (Google Sign-in)
- The app sends you to Google with scopes:
  - drive.readonly
  - documents.readonly
- You choose an account and approve.
- Google sends back a code → backend swaps it for tokens.
- Backend stores your tokens in-session (in-memory) and uses them to call Google APIs.

## 4) How we fetch Google Docs (own + shared + shared drives)
- We call Google Drive “files.list” with these filters/settings:
  - q:
    - mimeType='application/vnd.google-apps.document' and trashed=false
    - mimeType='application/vnd.google-apps.document' and trashed=false and sharedWithMe
  - includeItemsFromAllDrives=True
  - supportsAllDrives=True
  - corpora=allDrives
  - orderBy=modifiedTime desc
- This returns: your Docs, Docs shared with you, and Docs in shared drives.

## 5) How we extract text from Google Docs
- Use Google Docs API: documents.get(documentId)
- Walk the document body:
  - Paragraphs → text runs → collect content
  - Tables → cells → content → collect content
- Join all the text into one big string.

## 6) How we answer without OpenAI (fallback mode)
- We still do retrieval (find best chunks).
- We stitch the most relevant text snippets together.
- We format a clear, helpful answer from those snippets.
- If nothing is relevant, we clearly say: "Not found in your documents" and suggest how to proceed.

## 7) Deployment: env vars, secrets, HTTPS
- Environment variables (.env):
  - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, REDIRECT_URI
  - OPENAI_API_KEY (optional)
  - SECRET_KEY
- Secrets: never commit .env to Git.
- HTTPS: put FastAPI behind a reverse proxy like Nginx or a cloud platform (Render, Railway, Fly.io, GCP Cloud Run, AWS). Add your domain + TLS.
- Persistence: map ChromaDB directory to a volume or use a managed vector DB in production.

## One-liners you can use
- “RAG = search + generate. We store doc chunks as vectors so we can find relevant text fast.”
- “OAuth gives us a token to call Google APIs only with read-only scopes.”
- “If OpenAI isn’t available, we still answer from retrieved text snippets.”

## Bonus: How testers see the same Docs
- Add testers as OAuth ‘Test users’ in Google Cloud.
- Share Docs with their email (Viewer), or set “Anyone with the link → Viewer”.
- Our Drive query includes ‘sharedWithMe’ + shared drives.

---

### Print to PDF
- Open this file in your editor/preview → Print → Save as PDF.
- Or open on GitHub and use your browser’s Print → Save as PDF.
