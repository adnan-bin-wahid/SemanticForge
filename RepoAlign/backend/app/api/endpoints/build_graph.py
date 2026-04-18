from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from neo4j import Driver

from app.models.ingestion import IngestionRequest
from app.services.analysis_service import AnalysisService, get_analysis_service
from app.services.graph_builder import GraphBuilder
from app.db.neo4j_driver import get_neo4j_driver
from app.utils.directory_loader import DirectoryLoader

router = APIRouter()

class DirectoryPath(BaseModel):
    """Request body for loading a directory."""
    path: str

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

@router.post("/build-graph-from-directory", status_code=201, tags=["Graph"])
async def build_graph_from_directory_endpoint(
    dir_request: DirectoryPath,
    analysis_service: AnalysisService = Depends(get_analysis_service),
    driver: Driver = Depends(get_neo4j_driver)
):
    """
    Load all Python files from a directory, analyze them, and build the knowledge graph.
    
    This is useful for quick testing and development.
    
    Args:
        path: Absolute or relative path to the directory containing Python files
    """
    try:
        # Load all Python files from the directory
        ingestion_request = DirectoryLoader.load_directory(dir_request.path)
        
        # Analyze the repository
        analysis_result = analysis_service.analyze_repository(ingestion_request)
        
        # Build the graph
        graph_builder = GraphBuilder(driver)
        await graph_builder.create_graph_from_analysis(analysis_result)
        
        return {
            "message": "Graph built successfully from directory.",
            "files_analyzed": len(ingestion_request.files)
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

