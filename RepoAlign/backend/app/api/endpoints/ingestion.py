from fastapi import APIRouter
from ...models.ingestion import IngestionRequest
from ...utils.file_discovery import discover_python_files
from ...utils.ast_parser import parse_file_to_ast
from ...utils.structure_extractor import extract_structures

router = APIRouter()

@router.post("/ingest", tags=["Ingestion"])
async def ingest_repository(request: IngestionRequest):
    """
    Receives a repository path, discovers Python files, parses them,
    and extracts top-level functions and classes.
    """
    python_files = discover_python_files(request.repo_path)
    analysis_results = []
    failed_files = []

    for file_path in python_files:
        ast_tree = parse_file_to_ast(file_path)
        if ast_tree:
            structures = extract_structures(ast_tree)
            analysis_results.append({
                "file_path": file_path,
                "functions": structures["functions"],
                "classes": structures["classes"]
            })
        else:
            failed_files.append(file_path)
    
    return {
        "message": f"Analyzed {len(python_files)} Python files. Found {len(analysis_results)} parsable files. Failed to parse {len(failed_files)}.",
        "analysis_results": analysis_results,
        "failed_to_parse": failed_files
    }
