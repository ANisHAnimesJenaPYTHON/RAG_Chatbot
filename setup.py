"""Setup script for development"""

import subprocess
import sys
import os

def install_requirements():
    """Install Python requirements"""
    print("Installing Python dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    print("✓ Dependencies installed")

def create_env_file():
    """Create .env file from example if it doesn't exist"""
    if not os.path.exists(".env"):
        print("\nCreating .env file...")
        print("Please fill in your Google OAuth credentials and OpenAI API key:")
        print("1. Go to Google Cloud Console: https://console.cloud.google.com/")
        print("2. Create OAuth 2.0 credentials")
        print("3. Enable Google Drive API and Google Docs API")
        print("4. Add redirect URI: http://localhost:8000/auth/callback")
        print("\nCreate .env file with the following variables:")
        print("GOOGLE_CLIENT_ID=your_client_id")
        print("GOOGLE_CLIENT_SECRET=your_client_secret")
        print("OPENAI_API_KEY=your_openai_key (optional)")
        print("SECRET_KEY=your_random_secret_key")
        print("REDIRECT_URI=http://localhost:8000/auth/callback")
    else:
        print("✓ .env file already exists")

def create_directories():
    """Create necessary directories"""
    os.makedirs("chroma_db", exist_ok=True)
    print("✓ Directories created")

if __name__ == "__main__":
    try:
        install_requirements()
        create_directories()
        create_env_file()
        print("\n✓ Setup complete!")
        print("\nNext steps:")
        print("1. Fill in your .env file with credentials")
        print("2. Run: cd backend && python main.py")
        print("3. Open http://localhost:8000 in your browser")
    except Exception as e:
        print(f"Error during setup: {e}")
        sys.exit(1)

