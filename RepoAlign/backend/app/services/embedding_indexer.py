import asyncio
from qdrant_client.models import PointStruct, VectorParams, Distance
from ..db.neo4j_driver import get_neo4j_driver
from ..db.qdrant_client import get_qdrant_client
from .embeddings import generate_embedding

COLLECTION_NAME = "code_embeddings"
VECTOR_SIZE = 384  # Size of all-MiniLM-L6-v2 embeddings

class EmbeddingIndexer:
    """Service to build and maintain embeddings index for code symbols."""
    
    async def index_repository(self) -> dict:
        """
        Index all Function and Class nodes from Neo4j into Qdrant.
        
        Returns:
            A dictionary with indexing statistics
        """
        driver = get_neo4j_driver()
        qdrant = get_qdrant_client()
        loop = asyncio.get_event_loop()
        
        # Create collection if it doesn't exist
        try:
            await loop.run_in_executor(None, lambda: qdrant.get_collection(COLLECTION_NAME))
        except:
            await loop.run_in_executor(
                None,
                lambda: qdrant.create_collection(
                    collection_name=COLLECTION_NAME,
                    vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
                )
            )
        
        indexed_count = 0
        point_id = 0
        
        # Index Function nodes
        async with driver.session() as session:
            result = await session.run(
                "MATCH (f:Function) RETURN f.name as name, f.signature as signature, f.start_line as start_line"
            )
            async for record in result:
                name = record["name"]
                signature = record.get("signature", "")
                start_line = record.get("start_line", 0)
                
                # Create meaningful text for embedding
                text = f"Function: {name} {signature}"
                embedding = generate_embedding(text)
                
                # Store in Qdrant
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "type": "function",
                        "name": name,
                        "signature": signature,
                        "start_line": start_line,
                    }
                )
                await loop.run_in_executor(
                    None,
                    lambda p=point: qdrant.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[p],
                    )
                )
                
                point_id += 1
                indexed_count += 1
        
        # Index Class nodes
        async with driver.session() as session:
            result = await session.run(
                "MATCH (c:Class) RETURN c.name as name, c.start_line as start_line"
            )
            async for record in result:
                name = record["name"]
                start_line = record.get("start_line", 0)
                
                # Create meaningful text for embedding
                text = f"Class: {name}"
                embedding = generate_embedding(text)
                
                # Store in Qdrant
                point = PointStruct(
                    id=point_id,
                    vector=embedding,
                    payload={
                        "type": "class",
                        "name": name,
                        "start_line": start_line,
                    }
                )
                await loop.run_in_executor(
                    None,
                    lambda p=point: qdrant.upsert(
                        collection_name=COLLECTION_NAME,
                        points=[p],
                    )
                )
                
                point_id += 1
                indexed_count += 1
        
        return {
            "status": "success",
            "indexed_symbols": indexed_count,
            "collection": COLLECTION_NAME,
        }
