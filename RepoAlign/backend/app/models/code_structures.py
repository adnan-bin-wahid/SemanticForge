from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any

class CallDef(BaseModel):
    name: str
    lineno: int

class ParameterDef(BaseModel):
    name: str
    kind: str
    annotation: Optional[str] = None
    default: Optional[Any] = None

class SignatureDef(BaseModel):
    parameters: List[ParameterDef]
    return_annotation: Optional[str] = None

class FunctionDef(BaseModel):
    name: str
    lineno: int
    end_lineno: int
    signature: SignatureDef
    calls: List[CallDef]
    content: str

class ClassDef(BaseModel):
    name: str
    lineno: int
    end_lineno: int
    bases: List[str]
    methods: List[FunctionDef]
    content: str

class ImportDef(BaseModel):
    type: str
    lineno: int
    module: Optional[str] = None
    name: Optional[str] = None
    alias: Optional[str] = None
    level: Optional[int] = None

class FileReport(BaseModel):
    file_path: str
    functions: List[FunctionDef]
    classes: List[ClassDef]
    imports: List[ImportDef]

class AnalysisResult(BaseModel):
    files: List[FileReport]
