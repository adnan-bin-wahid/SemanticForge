from neo4j import Driver
from app.models.code_structures import AnalysisResult, FileReport, ClassDef, FunctionDef
import json

class GraphBuilder:
    def __init__(self, driver: Driver):
        self.driver = driver

    async def create_graph_from_analysis(self, analysis_data: AnalysisResult):
        """
        Main method to orchestrate graph creation from analysis data.
        """
        await self._create_repository_and_file_nodes(analysis_data)
        await self._create_class_and_function_nodes(analysis_data)
        await self._create_inheritance_relationships(analysis_data)
        await self._create_import_relationships(analysis_data)
        await self._create_call_relationships(analysis_data)

    async def _create_repository_and_file_nodes(self, analysis_data: AnalysisResult):
        repo_name = "AnalyzedRepository"

        async with self.driver.session() as session:
            # Clear the database for a fresh start
            await session.run("MATCH (n) DETACH DELETE n")

            # Create Repository node
            await session.run(
                "MERGE (r:Repository {name: $name})",
                name=repo_name,
            )

            # Create File and Module nodes and their relationships
            for file_report in analysis_data.files:
                await self._create_file_node(session, repo_name, file_report)

    async def _create_file_node(self, session, repo_name: str, file_report: FileReport):
        # Create File node and link it to the Repository
        cypher_file = """
        MATCH (r:Repository {name: $repo_name})
        MERGE (f:File {name: $file_name, path: $file_path})
        MERGE (r)-[:CONTAINS]->(f)
        """
        await session.run(
            cypher_file,
            repo_name=repo_name,
            file_name=file_report.file_path.split('/')[-1],
            file_path=file_report.file_path,
        )

    async def _create_class_and_function_nodes(self, analysis_data: AnalysisResult):
        async with self.driver.session() as session:
            for file_report in analysis_data.files:
                # Create Class nodes
                for class_def in file_report.classes:
                    cypher = """
                    MATCH (f:File {path: $file_path})
                    MERGE (c:Class {
                        name: $name,
                        start_line: $start_line,
                        end_line: $end_line,
                        content: $content
                    })
                    MERGE (f)-[:DEFINES]->(c)
                    """
                    await session.run(
                        cypher,
                        file_path=file_report.file_path,
                        name=class_def.name,
                        start_line=class_def.lineno,
                        end_line=class_def.end_lineno,
                        content=class_def.content,
                    )

                # Create Function nodes
                for func_def in file_report.functions:
                    signature_str = json.dumps({
                        "parameters": [p.dict() for p in func_def.signature.parameters],
                        "return_annotation": func_def.signature.return_annotation
                    })
                    cypher = """
                    MATCH (f:File {path: $file_path})
                    MERGE (func:Function {
                        name: $name,
                        signature: $signature,
                        start_line: $start_line,
                        end_line: $end_line,
                        content: $content
                    })
                    MERGE (f)-[:DEFINES]->(func)
                    """
                    await session.run(
                        cypher,
                        file_path=file_report.file_path,
                        name=func_def.name,
                        signature=signature_str,
                        start_line=func_def.lineno,
                        end_line=func_def.end_lineno,
                        content=func_def.content,
                    )

    async def _create_inheritance_relationships(self, analysis_data: AnalysisResult):
        async with self.driver.session() as session:
            for file_report in analysis_data.files:
                for class_def in file_report.classes:
                    if not class_def.bases:
                        continue

                    for base_class_name in class_def.bases:
                        cypher = """
                        MATCH (child:Class {name: $child_name})
                        MATCH (parent:Class {name: $parent_name})
                        MERGE (child)-[:INHERITS]->(parent)
                        """
                        await session.run(
                            cypher,
                            child_name=class_def.name,
                            parent_name=base_class_name,
                        )

    async def _create_import_relationships(self, analysis_data: AnalysisResult):
        async with self.driver.session() as session:
            for file_report in analysis_data.files:
                for import_def in file_report.imports:
                    if not import_def.module:
                        continue
                    
                    cypher = """
                    MATCH (f:File {path: $file_path})
                    MERGE (m:Module {name: $module_name})
                    MERGE (f)-[:IMPORTS]->(m)
                    """
                    await session.run(
                        cypher,
                        file_path=file_report.file_path,
                        module_name=import_def.module,
                    )

    async def _create_call_relationships(self, analysis_data: AnalysisResult):
        async with self.driver.session() as session:
            for file_report in analysis_data.files:
                for func_def in file_report.functions:
                    for call in func_def.calls:
                        cypher = """
                        MATCH (caller:Function {name: $caller_name})
                        MATCH (callee:Function {name: $callee_name})
                        MERGE (caller)-[:CALLS]->(callee)
                        """
                        await session.run(
                            cypher,
                            caller_name=func_def.name,
                            callee_name=call.name,
                        )
