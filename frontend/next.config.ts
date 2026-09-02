import type { NextConfig } from "next";
import path from "path";
import fs from "fs";

// --------------------------------------------------------------------------
// Load the root-level .env (one directory above frontend/) at config time.
// Next.js only looks for .env files inside the frontend/ directory, so we
// manually parse the root file and inject its variables into process.env
// before the Next.js env block is evaluated. No extra dependency needed.
// --------------------------------------------------------------------------
const rootEnvPath = path.resolve(__dirname, "../.env");
if (fs.existsSync(rootEnvPath)) {
  const lines = fs.readFileSync(rootEnvPath, "utf-8").split(/\r?\n/);
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#")) continue;
    const eqIdx = trimmed.indexOf("=");
    if (eqIdx < 1) continue;
    const key = trimmed.substring(0, eqIdx).trim();
    const value = trimmed.substring(eqIdx + 1).trim();
    // Only set if not already present (don't override shell environment)
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

const nextConfig: NextConfig = {
  env: {
    // Kidney graph
    KIDNEY_NEO4J_URI: process.env.KIDNEY_NEO4J_URI ?? "",
    KIDNEY_NEO4J_USERNAME: process.env.KIDNEY_NEO4J_USERNAME ?? "",
    KIDNEY_NEO4J_PASSWORD: process.env.KIDNEY_NEO4J_PASSWORD ?? "",
    KIDNEY_NEO4J_DATABASE: process.env.KIDNEY_NEO4J_DATABASE ?? "",

    // Cardio / generic graph
    NEO4J_URI: process.env.NEO4J_URI ?? "",
    NEO4J_USERNAME: process.env.NEO4J_USERNAME ?? "",
    NEO4J_PASSWORD: process.env.NEO4J_PASSWORD ?? "",
    NEO4J_DATABASE: process.env.NEO4J_DATABASE ?? "",

    // Retinopathy graph
    RETINOPATHY_NEO4J_URI: process.env.RETINOPATHY_NEO4J_URI ?? "",
    RETINOPATHY_NEO4J_USERNAME: process.env.RETINOPATHY_NEO4J_USERNAME ?? "",
    RETINOPATHY_NEO4J_PASSWORD: process.env.RETINOPATHY_NEO4J_PASSWORD ?? "",
    RETINOPATHY_NEO4J_DATABASE: process.env.RETINOPATHY_NEO4J_DATABASE ?? "",

    // Azure OpenAI
    AZURE_OPENAI_API_KEY: process.env.AZURE_OPENAI_API_KEY ?? "",
    AZURE_OPENAI_ENDPOINT: process.env.AZURE_OPENAI_ENDPOINT ?? "",
    AZURE_OPENAI_DEPLOYMENT_CLASSIFIER:
      process.env.AZURE_OPENAI_DEPLOYMENT_CLASSIFIER ?? "",
    AZURE_OPENAI_DEPLOYMENT_MAIN:
      process.env.AZURE_OPENAI_DEPLOYMENT_MAIN ?? "",
  },
};

export default nextConfig;
