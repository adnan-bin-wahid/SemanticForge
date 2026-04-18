from contextlib import asynccontextmanager
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient
import os

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")

qdrant_client: AsyncQdrantClient | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and manage Qdrant client lifecycle."""
    global qdrant_client
    # Initialize the Qdrant client
    qdrant_client = AsyncQdrantClient(url=QDRANT_URL)
    print("Connecting to Qdrant...")
    yield
    if qdrant_client:
        await qdrant_client.close()
        print("Disconnected from Qdrant.")

def get_qdrant_client() -> AsyncQdrantClient:
    global qdrant_client
    if qdrant_client is None:
        raise RuntimeError("Qdrant client not initialized.")
    return qdrant_client
