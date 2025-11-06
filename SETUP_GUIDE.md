# Setup Guide for RAG Chatbot with Google Docs Integration

This guide will help you set up and run the RAG-powered chatbot project.

## Prerequisites

- Python 3.8 or higher
- Google Cloud account
- (Optional) OpenAI API key for better LLM responses

## Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or use the setup script:

```bash
python setup.py
```

## Step 2: Google Cloud Console Setup

### 2.1 Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" → "New Project"
3. Give it a name (e.g., "RAG Chatbot")
4. Click "Create"

### 2.2 Enable Required APIs

1. In the Google Cloud Console, go to "APIs & Services" → "Library"
2. Enable the following APIs:
   - **Google Drive API**
   - **Google Docs API**

### 2.3 Create OAuth 2.0 Credentials

1. Go to "APIs & Services" → "Credentials"
2. Click "Create Credentials" → "OAuth client ID"
3. If prompted, configure the OAuth consent screen:
   - User Type: External (or Internal if using Google Workspace)
   - App name: "RAG Chatbot"
   - User support email: Your email
   - Developer contact: Your email
   - Save and continue through scopes (use default)
   - Add test users if needed
4. Create OAuth Client ID:
   - Application type: **Web application**
   - Name: "RAG Chatbot Web Client"
   - Authorized redirect URIs: 
     - `http://localhost:8000/auth/callback`
     - `http://127.0.0.1:8000/auth/callback`
   - Click "Create"
5. Copy the **Client ID** and **Client Secret**

## Step 3: Configure Environment Variables

Create a `.env` file in the project root directory:

```env
# Google OAuth Credentials
GOOGLE_CLIENT_ID=your_client_id_here
GOOGLE_CLIENT_SECRET=your_client_secret_here

# OAuth Redirect URI
REDIRECT_URI=http://localhost:8000/auth/callback

# OpenAI API Key (Optional - for better responses)
OPENAI_API_KEY=your_openai_api_key_here

# Session Secret (generate a random string)
SECRET_KEY=your_random_secret_key_minimum_32_characters_long

# Use local embeddings (true/false)
USE_LOCAL_EMBEDDINGS=true
```

### Generating a Secret Key

You can generate a random secret key using Python:

```python
import secrets
print(secrets.token_urlsafe(32))
```

Or use an online generator.

## Step 4: Run the Application

### Option 1: Using the run script

```bash
python run.py
```

### Option 2: Using uvicorn directly

```bash
cd backend
python main.py
```

Or:

```bash
uvicorn backend.main:app --reload --port 8000
```

### Option 3: From backend directory

```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

## Step 5: Access the Application

1. Open your web browser
2. Navigate to: `http://localhost:8000`
3. Click "Sign in with Google"
4. Authenticate with your Google account
5. Grant permissions for Google Drive and Docs access

## Usage

1. **Sign In**: Authenticate with your Google account
2. **View Documents**: Your Google Docs will be automatically fetched
3. **Select Documents**: Check the documents you want to add to the knowledge base
4. **Add to Knowledge Base**: Click "Add Selected to Knowledge Base"
5. **Chat**: Type questions in the chat interface
6. **Get Answers**: The chatbot will search your documents and provide answers

## Troubleshooting

### Issue: "Error fetching documents"

**Solution**: 
- Check that Google Drive API and Docs API are enabled
- Verify OAuth credentials are correct
- Ensure redirect URI matches exactly

### Issue: "No embedding model available"

**Solution**:
- If using local embeddings, the model will download automatically on first use
- If using OpenAI embeddings, set `USE_LOCAL_EMBEDDINGS=false` and provide `OPENAI_API_KEY`

### Issue: "Authentication failed"

**Solution**:
- Check OAuth redirect URI is exactly: `http://localhost:8000/auth/callback`
- Ensure the test user is added to OAuth consent screen (if using external user type)
- Clear browser cookies and try again

### Issue: "Module not found"

**Solution**:
- Ensure all dependencies are installed: `pip install -r requirements.txt`
- Check you're running from the correct directory
- Activate virtual environment if using one

### Issue: Port 8000 already in use

**Solution**:
- Change the port in `run.py` or when calling uvicorn: `--port 8001`
- Update `REDIRECT_URI` in `.env` to match the new port

## Project Structure

```
Project_Gyana/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── auth.py              # Google OAuth handling
│   ├── google_docs.py       # Google Docs API integration
│   ├── rag_pipeline.py      # RAG implementation
│   ├── models.py            # Pydantic models
│   └── config.py            # Configuration
├── frontend/
│   ├── index.html           # Main UI
│   ├── style.css            # Styling
│   └── app.js               # Frontend logic
├── chroma_db/               # Vector database (created automatically)
├── .env                     # Environment variables (create this)
├── requirements.txt         # Python dependencies
├── README.md                # Project documentation
└── run.py                   # Run script
```

## Features

✅ Google OAuth 2.0 Authentication  
✅ Fetch and display Google Docs  
✅ Select documents for knowledge base  
✅ RAG pipeline with vector search  
✅ Explicit fallback when answers not found in documents  
✅ Simple, interactive web interface  

## Next Steps

- Add support for Google Sheets and Slides (bonus feature)
- Implement document summarization
- Add multi-document querying
- Deploy to cloud platform (Heroku, AWS, etc.)

## Support

For issues or questions, refer to the main README.md or contact: hello@codemateai.dev

