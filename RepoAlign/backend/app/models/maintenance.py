"""
Pydantic models for Phase 8 maintenance operations
- Phase 8.5: Graph Invalidation
- Phase 8.6: Targeted Re-Analysis
"""

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


# ============= PHASE 8.5: Graph Invalidation Models =============

class SymbolChange(BaseModel):
    """Represents a change to a symbol"""
    symbol_name: str = Field(..., description="Name of the symbol")
    symbol_type: str = Field(..., description="Type of symbol (function or class)")


class ModifiedSymbol(BaseModel):
    """Represents a modified symbol with updated metadata"""
    symbol_name: str = Field(..., description="Name of the symbol")
    symbol_type: str = Field(..., description="Type of symbol (function or class)")
    new_signature: str = Field(..., description="New signature of the symbol")
    new_docstring: Optional[str] = Field(None, description="New docstring of the symbol")


class InvalidateFileChangesRequest(BaseModel):
    """Request for batch invalidating multiple symbol changes"""
    file_path: str = Field(..., description="Path to the file with changes")
    removed_symbols: List[SymbolChange] = Field(
        default=[], description="Symbols that were removed"
    )
    modified_symbols: List[ModifiedSymbol] = Field(
        default=[], description="Symbols that were modified"
    )


class InvalidateRemovedSymbolRequest(BaseModel):
    """Request for invalidating a single removed symbol"""
    file_path: str = Field(..., description="Path to the file containing the symbol")
    symbol_name: str = Field(..., description="Name of the removed symbol")
    symbol_type: str = Field(..., description="Type of symbol (function or class)")


class InvalidateModifiedSymbolRequest(BaseModel):
    """Request for invalidating a modified symbol"""
    file_path: str = Field(..., description="Path to the file containing the symbol")
    symbol_name: str = Field(..., description="Name of the modified symbol")
    symbol_type: str = Field(..., description="Type of symbol (function or class)")
    new_signature: str = Field(..., description="New signature of the symbol")
    new_docstring: Optional[str] = Field(None, description="New docstring")


class InvalidationImpactRequest(BaseModel):
    """Request for previewing invalidation impact"""
    file_path: str = Field(..., description="Path to the file containing the symbol")
    symbol_name: str = Field(..., description="Name of the symbol")
    symbol_type: str = Field(..., description="Type of symbol (function or class)")


# ============= PHASE 8.6: Re-Analysis Models =============

class ReAnalyzeFileChangesRequest(BaseModel):
    """Request for re-analyzing changed symbols in a file"""
    file_path: str = Field(..., description="Path to the file")
    file_content: str = Field(..., description="Current content of the file")
    added_symbols: List[SymbolChange] = Field(
        default=[], description="Symbols that were added"
    )
    modified_symbols: List[SymbolChange] = Field(
        default=[], description="Symbols that were modified"
    )


class ReAnalyzeSingleSymbolRequest(BaseModel):
    """Request for re-analyzing a single symbol"""
    file_path: str = Field(..., description="Path to the file")
    file_content: str = Field(..., description="Current content of the file")
    symbol_name: str = Field(..., description="Name of the symbol to analyze")
    symbol_type: str = Field(..., description="Type of symbol (function or class)")


class FileAnalysis(BaseModel):
    """Analysis for a single file"""
    file_path: str = Field(..., description="Path to the file")
    file_content: str = Field(..., description="Current content of the file")
    added_symbols: List[SymbolChange] = Field(
        default=[], description="Symbols that were added"
    )
    modified_symbols: List[SymbolChange] = Field(
        default=[], description="Symbols that were modified"
    )


class ReAnalyzeBatchRequest(BaseModel):
    """Request for batch re-analysis of multiple files"""
    file_analyses: List[FileAnalysis] = Field(
        ..., description="List of files and their symbol changes to analyze"
    )
