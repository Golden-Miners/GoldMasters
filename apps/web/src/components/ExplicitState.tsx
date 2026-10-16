import type { ReactNode } from "react";

export type ExplicitStateName =
  | "empty"
  | "loading"
  | "degraded"
  | "stale"
  | "no-setup"
  | "insufficient-evidence"
  | "conflicting-agents"
  | "schema-invalid"
  | "unavailable"
  | "offline";

const STATE_LABEL: Record<ExplicitStateName, string> = {
  empty: "No data available",
  loading: "Loading…",
  degraded: "Degraded — some data may be incomplete",
  stale: "Data is stale",
  "no-setup": "No setup configured",
  "insufficient-evidence": "Insufficient evidence",
  "conflicting-agents": "Conflicting agent outputs",
  "schema-invalid": "Schema invalid",
  unavailable: "Unavailable",
  offline: "Offline — backend unreachable",
};

export function ExplicitState({ state }: { state: ExplicitStateName }) {
  return (
    <p role="status" className={`explicit-state explicit-state-${state}`} data-testid={`state-${state}`}>
      {STATE_LABEL[state]}
    </p>
  );
}
