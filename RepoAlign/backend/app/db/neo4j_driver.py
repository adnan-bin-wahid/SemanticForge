from contextlib import asynccontextmanager
from fastapi import FastAPI
from neo4j import AsyncGraphDatabase, Driver, basic_auth
import os

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://neo4j:7687")

driver: Driver | None = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and manage Neo4j driver lifecycle."""
    global driver
    # Initialize the driver with Neo4j credentials
    driver = AsyncGraphDatabase.driver(NEO4J_URI, auth=basic_auth("neo4j", "password"), encrypted=False)
    print("Connecting to Neo4j...")
    yield
    if driver:
        await driver.close()
        print("Disconnected from Neo4j.")

def get_neo4j_driver() -> Driver:
    global driver
    if driver is None:
        raise RuntimeError("Neo4j driver not initialized.")
    return driver