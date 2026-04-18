from fastapi import APIRouter, Depends
from neo4j import Driver

from app.models.ingestion import IngestionRequest
from app.services.analysis_service import AnalysisService, get_analysis_service
from app.services.graph_builder import GraphBuilder
from app.db.neo4j_driver import get_neo4j_driver

router = APIRouter()

@router.post("/build-graph", status_code=201, tags=["Graph"])
async def build_graph_endpoint(
    request: IngestionRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    driver: Driver = Depends(get_neo4j_driver)
):
    """
    Orchestrates the full analysis and graph-building process.
    
    - Ingests repository content.
    - Analyzes the code to extract its structure.
    - Populates the Neo4j database with a complete static knowledge graph.
    """
    # 1. Analyze the repository
    analysis_result = analysis_service.analyze_repository(request)

    # 2. Build the graph
    graph_builder = GraphBuilder(driver)
    await graph_builder.create_graph_from_analysis(analysis_result)
    
    return {"message": "Graph built successfully."}
