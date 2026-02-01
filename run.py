#!/usr/bin/env python3
"""
Script to run the LUCICORE API server.
For development, set RELOAD=true environment variable.
"""
import os
import uvicorn

if __name__ == "__main__":
    reload = os.getenv("RELOAD", "false").lower() == "true"
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=reload
    )
