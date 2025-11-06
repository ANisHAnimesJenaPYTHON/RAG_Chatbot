"""Simple script to run the application"""

import uvicorn
import sys
from pathlib import Path

if __name__ == "__main__":
    # Add backend to path
    backend_path = Path(__file__).parent / "backend"
    sys.path.insert(0, str(backend_path.parent))
    
    print("Starting RAG Chatbot Server...")
    print("Open http://localhost:8000 in your browser")
    print("Press Ctrl+C to stop the server")
    
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

