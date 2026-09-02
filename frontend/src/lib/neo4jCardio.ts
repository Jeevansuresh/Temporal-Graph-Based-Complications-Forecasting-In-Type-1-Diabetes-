import neo4j, { Driver } from 'neo4j-driver';

const uri = process.env.CARDIO_NEO4J_URI || process.env.KIDNEY_NEO4J_URI || '';
const username = process.env.CARDIO_NEO4J_USERNAME || process.env.KIDNEY_NEO4J_USERNAME || '';
const password = process.env.CARDIO_NEO4J_PASSWORD || process.env.KIDNEY_NEO4J_PASSWORD || '';
const database = process.env.CARDIO_NEO4J_DATABASE || process.env.KIDNEY_NEO4J_DATABASE || undefined;

export const CARDIO_DATABASE = database;

let driver: Driver | null = null;

export function getCardioDriver() {
  if (!driver) {
    driver = neo4j.driver(uri, neo4j.auth.basic(username, password));
  }
  return driver;
}
