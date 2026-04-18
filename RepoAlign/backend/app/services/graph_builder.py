from neo4j import Driver
from app.models.ingestion import IngestionRequest, FileReport

class GraphBuilder:
    def __init__(self, driver: Driver):
        self.driver = driver

    async def create_graph_from_analysis(self, analysis_data: IngestionRequest):
        """
        Main method to orchestrate graph creation from analysis data.
        """
        # For now, we only implement file and module creation.
        # We will extend this in subsequent sub-phases.
        await self._create_repository_and_file_nodes(analysis_data)

    async def _create_repository_and_file_nodes(self, analysis_data: IngestionRequest):
        repo_name = "MyRepository" # Placeholder name
        repo_path = analysis_data.root_path

        async with self.driver.session() as session:
            # Clear the database for a fresh start
            await session.run("MATCH (n) DETACH DELETE n")

            # Create Repository node
            await session.run(
                "MERGE (r:Repository {name: $name, path: $path})",
                name=repo_name,
                path=repo_path,
            )

            # Create File and Module nodes and their relationships
            for file_report in analysis_data.files:
                await self._create_file_and_module_nodes_for_file(session, repo_name, file_report)

    async def _create_file_and_module_nodes_for_file(self, session, repo_name: str, file_report: FileReport):
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

        # Create Module nodes and link them to the File
        for imp in file_report.imports:
            cypher_module = """
            MATCH (f:File {path: $file_path})
            MERGE (m:Module {name: $module_name})
            MERGE (f)-[:IMPORTS]->(m)
            """
            await session.run(
                cypher_module,
                file_path=file_report.file_path,
                module_name=imp,
            )
