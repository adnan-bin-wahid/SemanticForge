import os
import requests
from fastapi import APIRouter

from app.db.neo4j_driver import get_neo4j_driver
from app.db.qdrant_client import get_qdrant_client

router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint to confirm the service is running.
    """
    return {"status": "ok"}


@router.get("/readiness", tags=["Health"])
async def readiness_check(model: str = "tinyllama"):
    """
    Readiness check for the full RepoAlign stack.

    Verifies:
    - FastAPI process
    - Neo4j connection
    - Qdrant connection
    - Ollama service and requested model availability
    """
    services = {
        "fastapi": {
            "status": "ok",
            "message": "FastAPI backend is reachable.",
        },
        "neo4j": {
            "status": "unknown",
            "message": "Neo4j has not been checked yet.",
        },
        "qdrant": {
            "status": "unknown",
            "message": "Qdrant has not been checked yet.",
        },
        "ollama": {
            "status": "unknown",
            "message": "Ollama has not been checked yet.",
        },
    }

    try:
        driver = get_neo4j_driver()
        async with driver.session() as session:
            result = await session.run("RETURN 1 AS ok")
            record = await result.single()
            if record and record["ok"] == 1:
                services["neo4j"] = {
                    "status": "ok",
                    "message": "Neo4j connection is ready.",
                }
            else:
                services["neo4j"] = {
                    "status": "error",
                    "message": "Neo4j responded unexpectedly.",
                }
    except Exception as e:
        services["neo4j"] = {
            "status": "error",
            "message": f"Neo4j is not ready: {str(e)}",
        }

    try:
        qdrant = get_qdrant_client()
        collections = qdrant.get_collections()
        services["qdrant"] = {
            "status": "ok",
            "message": "Qdrant connection is ready.",
            "collections": len(collections.collections),
        }
    except Exception as e:
        services["qdrant"] = {
            "status": "error",
            "message": f"Qdrant is not ready: {str(e)}",
        }

    ollama_url = os.getenv("OLLAMA_URL", "http://ollama:11434").rstrip("/")
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        models = response.json().get("models", [])
        model_names = [item.get("name", "") for item in models]
        model_ready = any(
            name == model or name.startswith(f"{model}:") for name in model_names
        )

        if model_ready:
            services["ollama"] = {
                "status": "ok",
                "message": f"Ollama is ready and model '{model}' is available.",
                "models": model_names,
            }
        else:
            services["ollama"] = {
                "status": "error",
                "message": f"Ollama is reachable, but model '{model}' is not installed.",
                "models": model_names,
            }
    except Exception as e:
        services["ollama"] = {
            "status": "error",
            "message": f"Ollama is not ready: {str(e)}",
        }

    ready = all(service["status"] == "ok" for service in services.values())
    return {
        "status": "ready" if ready else "not_ready",
        "ready": ready,
        "model": model,
        "services": services,
    }
