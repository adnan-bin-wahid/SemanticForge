from typing import List
import ast

from app.models.ingestion import IngestionRequest
from app.models.code_structures import (
    AnalysisResult,
    FileReport,
    FunctionDef,
    ClassDef,
    ImportDef,
)
from app.utils.structure_extractor import StructureExtractor


class AnalysisService:
    def analyze_repository(self, request: IngestionRequest) -> AnalysisResult:
        file_reports: List[FileReport] = []

        for file_content in request.files:
            try:
                tree = ast.parse(file_content.content)
                if tree:
                    extractor = StructureExtractor(root_path=".")
                    extractor.visit(tree)

                    # Convert dicts to Pydantic models
                    functions = [FunctionDef(**f) for f in extractor.functions]
                    classes = [ClassDef(**c) for c in extractor.classes]
                    imports = [ImportDef(**i) for i in extractor.imports]

                    report = FileReport(
                        file_path=file_content.path,
                        imports=imports,
                        classes=classes,
                        functions=functions,
                    )
                    file_reports.append(report)
            except Exception as e:
                print(f"Error analyzing file {file_content.path}: {e}")

        return AnalysisResult(files=file_reports)


def get_analysis_service() -> AnalysisService:
    return AnalysisService()


