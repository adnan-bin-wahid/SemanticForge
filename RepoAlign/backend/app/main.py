from fastapi import FastAPI
from .api.endpoints import health, ingestion

app = FastAPI(title="RepoAlign Backend")

app.include_router(health.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
