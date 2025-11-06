# Quick Start Guide

Get up and running in 5 minutes!

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

## 2. Set Up Google OAuth

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project and enable **Google Drive API** and **Google Docs API**
3. Create OAuth 2.0 credentials (Web application)
4. Add redirect URI: `http://localhost:8000/auth/callback`
5. Copy Client ID and Client Secret

## 3. Create .env File

Create `.env` in project root:

```env
GOOGLE_CLIENT_ID=your_client_id
GOOGLE_CLIENT_SECRET=your_client_secret
REDIRECT_URI=http://localhost:8000/auth/callback
OPENAI_API_KEY=your_key_optional
SECRET_KEY=generate_random_string_here
USE_LOCAL_EMBEDDINGS=true
```

## 4. Run

```bash
python run.py
```

Open `http://localhost:8000` in your browser!

## That's It! 🎉

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md)

