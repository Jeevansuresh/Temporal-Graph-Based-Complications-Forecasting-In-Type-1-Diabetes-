"""Minimal connectivity check for the Retinopathy Neo4j driver.

Requires a running Neo4j instance reachable via RETINOPATHY_NEO4J_* env vars
(see Retinopathy/.env.example). Does not touch nodes, relationships, rules,
evidence, or patient data.
"""

from app.graph.connection import verify_connectivity


def test_verify_connectivity():
    assert verify_connectivity() is True
