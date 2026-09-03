import OpenAI from 'openai';

const apiKey = process.env.AZURE_OPENAI_API_KEY || '';
const endpoint = process.env.AZURE_OPENAI_ENDPOINT || '';

let client: OpenAI | null = null;

export function getOpenAIClient() {
  if (!client) {
    const isV1Endpoint = endpoint.includes('/openai/v1') || endpoint.includes('/v1');
    client = new OpenAI({
      apiKey,
      baseURL: endpoint,
      ...(isV1Endpoint ? {} : { defaultQuery: { 'api-version': '2024-02-15-preview' } }),
      defaultHeaders: { 'api-key': apiKey },
    });
  }
  return client;
}
