from pydantic import BaseModel
from typing import List

class FileContent(BaseModel):
    """
    Represents a single file with its path and content.
    """
    path: str  # The relative path of the file in the project
    content: str

class IngestionRequest(BaseModel):
    """
    Request model for the ingestion endpoint, containing file contents.
    """
    files: List[FileContent]

