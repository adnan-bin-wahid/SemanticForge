from fastapi import APIRouter
from ...models.ingestion import IngestionRequest
from ...utils.file_discovery import discover_python_files

router = APIRouter()

@router.post("/ingest", tags=["Ingestion"])
async def ingest_repository(request: IngestionRequest):
    """
    Receives a repository path, discovers all Python files,
    and returns the list of discovered files.
    """
    python_files = discover_python_files(request.repo_path)
    
    return {
        "message": f"Successfully discovered {len(python_files)} Python files.",
        "files": python_files
    }
