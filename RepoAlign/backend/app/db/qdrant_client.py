from contextlib import asynccontextmanager
from fastapi import FastAPI
from qdrant_client import QdrantClient
import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

qdrant_client: QdrantClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and manage Qdrant client lifecycle."""
    global qdrant_client
    # Initialize the Qdrant client with synchronous client
    qdrant_client = QdrantClient(url=QDRANT_URL)
    print("Connecting to Qdrant...")
    yield
    if qdrant_client:
        # Sync client doesn't need async close
        print("Disconnected from Qdrant.")

def get_qdrant_client() -> QdrantClient:
    global qdrant_client
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized.")
    return qdrant_client
