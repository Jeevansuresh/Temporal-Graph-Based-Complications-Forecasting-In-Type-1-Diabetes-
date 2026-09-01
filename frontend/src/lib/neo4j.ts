import neo4j, { Driver } from 'neo4j-driver';

const uri = process.env.KIDNEY_NEO4J_URI || '';
const username = process.env.KIDNEY_NEO4J_USERNAME || '';
const password = process.env.KIDNEY_NEO4J_PASSWORD || '';

if (!uri || !username || !password) {
  console.warn('Neo4j credentials are not set in environment variables');
}

let driver: Driver | null = null;

export function getNeo4jDriver() {
  if (!driver) {
    driver = neo4j.driver(uri, neo4j.auth.basic(username, password));
  }
  return driver;
}
