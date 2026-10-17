import type { ErrorPayload } from "../generated/error";
import type { DecisionRecord } from "../generated/decision";
import type { BacktestRecord } from "../generated/backtest";
import type { JournalEntry } from "../generated/journal";
import type { MarketBar } from "../generated/market";

const API_BASE_URL =
  process.env.GOLDMASTERS_API_BASE_URL ?? "http://127.0.0.1:8000";

export interface HealthBody {
  status: string;
  version: string;
  contract_schema_version: string;
  config_hash: string;
  database: { reachable: boolean };
  provider: object;
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

export async function fetchDecisions(): Promise<
  | { available: true; decisions: DecisionRecord[] }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/decisions`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const decisions = (await response.json()) as DecisionRecord[];
    return { available: true, decisions };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchNewsSentiment(): Promise<
  | { available: true; data: { status: string; items: unknown[]; limitations: string[] } }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/news-sentiment`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const data = (await response.json()) as { status: string; items: unknown[]; limitations: string[] };
    return { available: true, data };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchStrategies(): Promise<
  | { available: true; agents: Array<{ agent_id: string; enabled: boolean; instruments: string[]; timeframes: string[]; regimes: string[]; min_bars: number }> }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/strategies`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const agents = (await response.json()) as Array<{ agent_id: string; enabled: boolean; instruments: string[]; timeframes: string[]; regimes: string[]; min_bars: number }>;
    return { available: true, agents };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchBacktests(): Promise<
  | { available: true; records: BacktestRecord[] }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/backtests`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const records = (await response.json()) as BacktestRecord[];
    return { available: true, records };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchJournal(): Promise<
  | { available: true; entries: JournalEntry[] }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/journal`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const entries = (await response.json()) as JournalEntry[];
    return { available: true, entries };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchAgentRuns(): Promise<
  | { available: true; data: { status: string; runs: unknown[]; limitations: string[] } }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/agent-runs`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const data = (await response.json()) as { status: string; runs: unknown[]; limitations: string[] };
    return { available: true, data };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchProviders(): Promise<
  | { available: true; data: object }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/providers`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const data = await response.json();
    return { available: true, data };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchModelHealth(): Promise<
  | { available: true; data: { status: string; endpoint: string; expected_model: string | null; limitations: string[] } }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/model-health`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const data = (await response.json()) as { status: string; endpoint: string; expected_model: string | null; limitations: string[] };
    return { available: true, data };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchSettings(): Promise<
  | { available: true; config: Record<string, unknown> }
  | { available: false; reason: string }
> {
  try {
    const response = await fetch(`${API_BASE_URL}/v1/settings`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const config = (await response.json()) as Record<string, unknown>;
    return { available: true, config };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}

export async function fetchMarketBars(
  instrument_id: string = "xauusd",
  timeframe: string = "H1",
  count?: number
): Promise<
  | { available: true; bars: MarketBar[] }
  | { available: false; reason: string }
> {
  const params = new URLSearchParams({ instrument_id, timeframe });
  if (count !== undefined) params.set("count", String(count));
  try {
    const response = await fetch(`${API_BASE_URL}/v1/market/bars?${params}`, { cache: "no-store" });
    if (!response.ok) {
      return { available: false, reason: `API answered ${response.status}` };
    }
    const bars = (await response.json()) as MarketBar[];
    return { available: true, bars };
  } catch {
    return { available: false, reason: "API unreachable" };
  }
}