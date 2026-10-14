import type { ErrorPayload } from "../generated/error";

const API_BASE_URL =
  process.env.GOLDMASTERS_API_BASE_URL ?? "http://127.0.0.1:8000";

// HealthBody mirrors the backend's five-field /health surface
// (apps/api/src/goldmasters_api/health.py); its field names are pinned by
// tests/integration/test_health.py so the page cannot drift from the API.
// Failure bodies use the generated C-09 ErrorPayload — no contract shape is
// hand-written in this module.
export interface HealthBody {
  status: string;
  version: string;
  contract_schema_version: string;
  config_hash: string;
  database: { reachable: boolean };
}

export type HealthResult =
  | { available: true; health: HealthBody }
  | { available: false; reason: string };

export async function fetchHealth(timeoutMs = 5000): Promise<HealthResult> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!response.ok) {
      const failure = (await response.json().catch(() => null)) as ErrorPayload | null;
      const detail = failure?.message ? `: ${failure.message}` : "";
      return { available: false, reason: `API answered ${response.status}${detail}` };
    }
    const body = (await response.json()) as HealthBody;
    return { available: true, health: body };
  } catch {
    return { available: false, reason: "API unreachable" };
  } finally {
    clearTimeout(timer);
  }
}
