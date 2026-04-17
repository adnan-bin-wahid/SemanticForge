from pathlib import Path
from typing import List

from app.models.code_structures import AnalysisResult, FileReport
from app.utils.file_discovery import discover_python_files
from app.utils.ast_parser import parse_file_to_ast
from app.utils.structure_extractor import StructureExtractor

class AnalysisService:
    def analyze_repository(self, repo_path: Path) -> AnalysisResult:
        python_files = discover_python_files(str(repo_path))
        file_reports: List[FileReport] = []

        for file_path in python_files:
            try:
                tree = parse_file_to_ast(file_path)
                if tree:
                    extractor = StructureExtractor(str(repo_path))
                    extractor.visit(tree)
                    
                    # Create a FileReport Pydantic model
                    report = FileReport(
                        file_path=file_path.replace(str(repo_path), "", 1).lstrip("/\\"),
                        imports=extractor.imports,
                        classes=[
                            cls.copy(deep=True) for cls in extractor.classes
                        ],
                        functions=[
                            func.copy(deep=True) for func in extractor.functions
                        ]
                    )
                    file_reports.append(report)
            except Exception as e:
                print(f"Error analyzing file {file_path}: {e}")

        return AnalysisResult(files=file_reports)

def get_analysis_service() -> AnalysisService:
    return AnalysisService()
