from fastapi import APIRouter, Depends

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
    Receives a list of file contents, parses them,
    and extracts their structure using the AnalysisService.
    """
    analysis_result = analysis_service.analyze_repository(request)
    return analysis_result


