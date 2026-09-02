import neo4j, { Driver } from 'neo4j-driver';

const uri = process.env.RETINOPATHY_NEO4J_URI || '';
const username = process.env.RETINOPATHY_NEO4J_USERNAME || '';
const password = process.env.RETINOPATHY_NEO4J_PASSWORD || '';
const database = process.env.RETINOPATHY_NEO4J_DATABASE || undefined;

export const RETINOPATHY_DATABASE = database;

if (!uri || !username || !password) {
  console.warn('Retinopathy Neo4j credentials are not set in environment variables');
}

let driver: Driver | null = null;

export function getRetinopathyDriver() {
  if (!driver) {
    driver = neo4j.driver(uri, neo4j.auth.basic(username, password));
  }
  return driver;
}
