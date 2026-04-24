from contextlib import asynccontextmanager
from fastapi import FastAPI
from .api.endpoints import health, ingestion, graph, build_graph, embeddings, validation
from .db import neo4j_driver, qdrant_client
from .services.graph_expansion import GraphExpansion
from .services.context_retriever import ContextRetriever
from .services.code_generation import CodeGenerator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize both Neo4j and Qdrant on startup
    async with neo4j_driver.lifespan(app):
        async with qdrant_client.lifespan(app):
            graph_expansion_service = GraphExpansion()
            app.state.graph_expansion_service = graph_expansion_service
            context_retriever = ContextRetriever(graph_expansion_service)
            app.state.context_retriever = context_retriever
            app.state.code_generator = CodeGenerator(context_retriever, "http://ollama:11434")
            yield
            graph_expansion_service.close()

app = FastAPI(title="RepoAlign Backend", lifespan=lifespan)

app.include_router(health.router, prefix="/api/v1")
app.include_router(ingestion.router, prefix="/api/v1")
app.include_router(graph.router, prefix="/api/v1")
app.include_router(build_graph.router, prefix="/api/v1")
app.include_router(embeddings.router, prefix="/api/v1")
app.include_router(validation.router, prefix="/api/v1")

