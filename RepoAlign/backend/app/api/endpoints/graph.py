from fastapi import APIRouter, Depends, HTTPException
from neo4j import Driver
from app.db.neo4j_driver import get_neo4j_driver
from app.services.graph_builder import GraphBuilder
from app.models.code_structures import AnalysisResult

router = APIRouter()

@router.post("/build-graph-from-analysis", status_code=201, tags=["Graph"])
async def build_graph_from_analysis_endpoint(
    analysis_result: AnalysisResult,
    driver: Driver = Depends(get_neo4j_driver)
):
    """
    Receives repository analysis data (as a JSON body), builds a knowledge graph,
    and stores it in Neo4j. This is useful for debugging or re-building the graph
    from a saved analysis result.
    """
    try:
        graph_builder = GraphBuilder(driver)
        await graph_builder.create_graph_from_analysis(analysis_result)
        return {"message": "Graph built successfully from analysis data."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
