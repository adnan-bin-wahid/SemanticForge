from fastapi import APIRouter, Depends, HTTPException
from ..models.ingestion import IngestionRequest

router = APIRouter()

@router.post("/ingest", tags=["Ingestion"])
async def ingest_repository(request: IngestionRequest):
    """
    Receives a repository path and validates it.
    
    This is a non-functional endpoint for now. It just confirms
    that the path is a valid, existing directory.
    """
    # The Pydantic model `DirectoryPath` already validates that the path exists
    # and is a directory. If the validation fails, FastAPI will automatically
    # return a 422 Unprocessable Entity response.
    
    return {"message": "Repository path received and validated successfully.", "path": request.repo_path}
