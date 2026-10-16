import type { BacktestRecord } from "../generated/backtest";
import type { DecisionRecord } from "../generated/decision";
import type { ErrorPayload } from "../generated/error";
import type { JournalEntry } from "../generated/journal";

const API_BASE_URL =
  process.env.GOLDMASTERS_API_BASE_URL ?? "http://127.0.0.1:8000";

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

async function get<T>(path: string): Promise<T | { error: ErrorPayload }> {
  const response = await fetch(`${API_BASE_URL}${path}`, { cache: "no-store" });
  const body = (await response.json()) as T | ErrorPayload;
  if (!response.ok) return { error: body as ErrorPayload };
  return body as T;
}

export const fetchDecisions = () => get<DecisionRecord[]>("/v1/decisions");
export const fetchNewsSentiment = () =>
  get<{ status: string; items: unknown[]; limitations: string[] }>("/v1/news-sentiment");
export const fetchStrategies = () =>
  get<Array<Record<string, unknown>>>("/v1/strategies");
export const fetchBacktests = () => get<BacktestRecord[]>("/v1/backtests");
export const fetchJournal = () => get<JournalEntry[]>("/v1/journal");
export const fetchAgentRuns = () =>
  get<{ status: string; runs: unknown[]; limitations: string[] }>("/v1/agent-runs");
export const fetchProviders = () => get<Record<string, unknown>>("/v1/providers");
export const fetchModelHealth = () =>
  get<{ status: string; endpoint: string; expected_model: string | null; limitations: string[] }>(
    "/v1/model-health",
  );
export const fetchSettings = () => get<Record<string, unknown>>("/v1/settings");
