from neo4j import GraphDatabase, Driver
from contextlib import asynccontextmanager
from fastapi import FastAPI

# Connection details for the Neo4j container
NEO4J_URI = "bolt://neo4j:7687"
# We disabled auth in docker-compose, so no user/pass needed
NEO4J_USER = ""
NEO4J_PASSWORD = ""

class Neo4jConnection:
    def __init__(self, uri: str, user: str, password: str):
        self.driver: Driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    async def verify_connectivity(self):
        """
        Verifies that the driver can connect to the database.
        Raises an exception if the connection fails.
        """
        await self.driver.verify_connectivity()

db_connection = Neo4jConnection(NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # On startup, verify connection
    try:
        await db_connection.driver.verify_connectivity()
        print("Successfully connected to Neo4j.")
    except Exception as e:
        print(f"Failed to connect to Neo4j: {e}")
    
    yield
    
    # On shutdown, close the connection
    print("Closing Neo4j connection.")
    db_connection.close()

def get_db_driver() -> Driver:
    return db_connection.driver
