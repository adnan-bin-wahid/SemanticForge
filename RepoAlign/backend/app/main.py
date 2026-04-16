from fastapi import FastAPI
from .api.endpoints import health

app = FastAPI(title="RepoAlign Backend")

app.include_router(health.router, prefix="/api/v1")
