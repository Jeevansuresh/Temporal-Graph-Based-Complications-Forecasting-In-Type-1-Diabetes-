"""Neo4j connection configuration for the Retinopathy module.

Reads RETINOPATHY_NEO4J_* variables from the environment (populated via
.env locally; see Retinopathy/.env.example). Kept separate from Kidney's
KIDNEY_NEO4J_* variables so both modules can share a single .env safely.
"""

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Resolve the project root .env regardless of where the script is invoked from.
# This file lives at Retinopathy/app/graph/config.py so the root is 3 levels up.
_ROOT_ENV = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ROOT_ENV)


@dataclass(frozen=True)
class Neo4jConfig:
    uri: str
    username: str
    password: str
    database: str


def load_config() -> Neo4jConfig:
    uri = os.getenv("RETINOPATHY_NEO4J_URI", "bolt://localhost:7687")
    username = os.getenv("RETINOPATHY_NEO4J_USERNAME", "neo4j")
    password = os.getenv("RETINOPATHY_NEO4J_PASSWORD")
    database = os.getenv("RETINOPATHY_NEO4J_DATABASE", "neo4j")

    if not password:
        raise RuntimeError(
            "RETINOPATHY_NEO4J_PASSWORD is not set. "
            "Copy Retinopathy/.env.example to Retinopathy/.env and fill in credentials."
        )

    return Neo4jConfig(uri=uri, username=username, password=password, database=database)
