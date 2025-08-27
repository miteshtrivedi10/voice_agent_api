from dotenv import load_dotenv
import uvicorn
from fastapi import FastAPI, Depends
from fastapi.security import HTTPBearer
from starlette.middleware.cors import CORSMiddleware
from loguru import logger
import os
import sys

from logic.api import router

app = FastAPI(title="Voice Tutor Agent API")

# Configure loguru for console output with Uvicorn-like format
logger.remove()
logger.add(
    sys.stdout,
    level="INFO",
    format="{level}:     {message}",
    colorize=False
)
logger.info("Application starting...")

_ = load_dotenv(override=True)

# Include API router with authentication
app.include_router(router)


# Health check endpoint (no authentication required)
@app.get("/healthz")
async def health_check():
    logger.info("Health check endpoint called")
    return {"status": "healthy"}


app.add_middleware(
    CORSMiddleware,
    allow_origins="*",
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup"""
    logger.info("Application started successfully")
    # Create necessary directories
    os.makedirs("uploaded_files", exist_ok=True)
    os.makedirs("logs", exist_ok=True)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, loop="asyncio")
