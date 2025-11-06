"""Quick script to check configuration"""
from backend.config import settings

print("Configuration Check:")
print(f"Google Client ID: {'✓ Set' if settings.google_client_id else '✗ NOT SET'}")
print(f"Google Client Secret: {'✓ Set' if settings.google_client_secret else '✗ NOT SET'}")
print(f"Redirect URI: {settings.redirect_uri}")

if not settings.google_client_id or not settings.google_client_secret:
    print("\n⚠️  WARNING: Google OAuth credentials not configured!")
    print("Please create a .env file with:")
    print("  GOOGLE_CLIENT_ID=your_client_id")
    print("  GOOGLE_CLIENT_SECRET=your_client_secret")

