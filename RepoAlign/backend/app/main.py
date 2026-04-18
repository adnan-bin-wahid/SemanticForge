from fastapi import FastAPI
from .api.endpoints import health, ingestion, graph, build_graph
from .db.neo4j_driver import lifespan

app = FastAPI(title="RepoAlign Backend", lifespan=lifespan)

app.include_router(health.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(build_graph.router, prefix="/api/v1")

