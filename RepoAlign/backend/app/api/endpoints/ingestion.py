from fastapi import APIRouter, Depends
from pathlib import Path

from app.models.ingestion import IngestionRequest
from app.models.code_structures import AnalysisResult
from app.services.analysis_service import AnalysisService, get_analysis_service

router = APIRouter()

@router.post("/ingest", response_model=AnalysisResult, tags=["Ingestion"])
async def ingest_repository(
    request: IngestionRequest,
    analysis_service: AnalysisService = Depends(get_analysis_service)
):
    """
    Receives a repository path, discovers Python files, parses them,
    and extracts their structure using the AnalysisService.
    """
    repo_path = Path(request.repo_path)
    analysis_result = analysis_service.analyze_repository(repo_path)
    return analysis_result

