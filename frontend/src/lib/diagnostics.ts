import { API_BASE_URL } from "./apiConfig";

export interface PipelineHealth {
  ingestion_engine: { active: boolean };
  ml_classifier: { loaded: boolean; model_type: string | null };
}

export async function fetchPipelineHealth(): Promise<PipelineHealth | null> {
  try {
    const res = await fetch(`${API_BASE_URL}/health/pipeline`);
    if (!res.ok) return null;
    return (await res.json()) as PipelineHealth;
  } catch {
    return null;
  }
}
