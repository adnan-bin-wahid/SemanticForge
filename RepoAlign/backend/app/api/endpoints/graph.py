from fastapi import APIRouter, Depends
from neo4j import Driver
from app.db.neo4j_driver import get_neo4j_driver
from app.services.analysis_service import AnalysisService
from app.services.graph_builder import GraphBuilder
from app.models.ingestion import IngestionRequest

router = APIRouter()

@router.post("/build-graph", status_code=201)
async def build_graph_endpoint(
    ingestion_request: InestionRequest,
    driver: Driver = Depends(get_neo4j_driver)
):
    """
    Receives repository analysis data, builds a knowledge graph,
    and stores it in Neo4j.
    """
    graph_builder = GraphBuilder(driver)
    await graph_builder.create_graph_from_analysis(ingestion_request)
    return {"message": "Graph built successfully from analysis data."}
