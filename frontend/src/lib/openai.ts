import OpenAI from 'openai';

const apiKey = process.env.AZURE_OPENAI_API_KEY || '';
const endpoint = process.env.AZURE_OPENAI_ENDPOINT || '';

let client: OpenAI | null = null;

export function getOpenAIClient() {
  if (!client) {
    client = new OpenAI({
      apiKey,
      baseURL: endpoint,
      defaultQuery: { 'api-version': '2024-02-15-preview' },
      defaultHeaders: { 'api-key': apiKey },
    });
  }
  return client;
}
