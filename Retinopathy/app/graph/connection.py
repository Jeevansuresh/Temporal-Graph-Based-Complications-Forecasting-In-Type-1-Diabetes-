"""Driver lifecycle for the Retinopathy Neo4j connection.

This module only manages the connection. It does not load or query
nodes, relationships, rules, evidence, or patient data.
"""

from contextlib import contextmanager

from neo4j import Driver, GraphDatabase

from app.graph.config import Neo4jConfig, load_config


def get_driver(config: Neo4jConfig | None = None) -> Driver:
    config = config or load_config()
    return GraphDatabase.driver(config.uri, auth=(config.username, config.password))


@contextmanager
def neo4j_driver(config: Neo4jConfig | None = None):
    driver = get_driver(config)
    try:
        yield driver
    finally:
        driver.close()


def verify_connectivity() -> bool:
    config = load_config()
    with neo4j_driver(config) as driver:
        driver.verify_connectivity()
        return True


@contextmanager
def neo4j_session(config: Neo4jConfig | None = None):
    config = config or load_config()
    with neo4j_driver(config) as driver:
        with driver.session(database=config.database) as session:
            yield session
