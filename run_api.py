#!/usr/bin/env python3
"""
Run FastAPI backend server
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",  # Use import string for reload support
        host="0.0.0.0",
        port=8000,
        reload=True  # Auto-reload on code changes
    )
