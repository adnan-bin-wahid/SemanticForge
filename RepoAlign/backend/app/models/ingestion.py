from pydantic import BaseModel, DirectoryPath

class IngestionRequest(BaseModel):
    """
    Request model for the ingestion endpoint.
    """
    repo_path: DirectoryPath
