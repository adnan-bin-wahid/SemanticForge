from fastapi import APIRouter
from ...models.ingestion import IngestionRequest
from ...utils.file_discovery import discover_python_files
from ...utils.ast_parser import parse_file_to_ast

router = APIRouter()

@router.post("/ingest", tags=["Ingestion"])
async def ingest_repository(request: IngestionRequest):
    """
    Receives a repository path, discovers all Python files,
    parses them into ASTs, and returns the results.
    """
    python_files = discover_python_files(request.repo_path)
    parsed_files = 0
    failed_files = []

    for file_path in python_files:
        ast_tree = parse_file_to_ast(file_path)
        if ast_tree:
            parsed_files += 1
        else:
            failed_files.append(file_path)
    
    return {
        "message": f"Discovered {len(python_files)} Python files. Successfully parsed {parsed_files}. Failed to parse {len(failed_files)}.",
        "discovered_files": python_files,
        "failed_to_parse": failed_files
    }
