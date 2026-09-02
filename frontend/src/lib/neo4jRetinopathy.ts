import neo4j, { Driver } from 'neo4j-driver';

const uri = process.env.RETINOPATHY_NEO4J_URI || process.env.NEO4J_URI || process.env.KIDNEY_NEO4J_URI || '';
const username = process.env.RETINOPATHY_NEO4J_USERNAME || process.env.NEO4J_USERNAME || process.env.KIDNEY_NEO4J_USERNAME || '';
const password = process.env.RETINOPATHY_NEO4J_PASSWORD || process.env.NEO4J_PASSWORD || process.env.KIDNEY_NEO4J_PASSWORD || '';
const database = process.env.RETINOPATHY_NEO4J_DATABASE || process.env.NEO4J_DATABASE || process.env.KIDNEY_NEO4J_DATABASE || undefined;

export const RETINOPATHY_DATABASE = database;

let driver: Driver | null = null;

export function getRetinopathyDriver() {
  if (!driver) {
    driver = neo4j.driver(uri, neo4j.auth.basic(username, password));
  }
  return driver;
}
