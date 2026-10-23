"use client";

import type { FC, ReactNode } from "react";
import { StatusBadge } from "./StatusBadge";

type ExplicitState =
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

interface ExplicitStateProps {
  state: ExplicitState;
  children?: ReactNode;
  /** Optional action button for states that offer one (e.g., retry). */
  action?: { label: string; onClick: () => void };
}

/**
 * ExplicitState renders one of ten closed states with dark-theme styling.
 * Each state maps to a CSS class derived from the design tokens.
 * Unknown is never styled healthy.
 */
const toneClass: Record<ExplicitState, string> = {
  empty: "gm-explicit-state-neutral",
  loading: "gm-explicit-state-neutral",
  degraded: "gm-explicit-state-warning",
  stale: "gm-explicit-state-warning",
  "no-setup": "gm-explicit-state-neutral",
  "insufficient-evidence": "gm-explicit-state-warning",
  "conflicting-agents": "gm-explicit-state-warning",
  "schema-invalid": "gm-explicit-state-blocked",
  unavailable: "gm-explicit-state-blocked",
  offline: "gm-explicit-state-blocked",
};

const stateMap: Record<ExplicitState, { label: string; description: string }> = {
  empty: { label: "Empty", description: "No data available." },
  loading: { label: "Loading", description: "Fetching live state." },
  degraded: { label: "Degraded", description: "Partial data; some sources unavailable." },
  stale: { label: "Stale", description: "Data freshness exceeded threshold." },
  "no-setup": { label: "No Setup", description: "No qualifying setup found." },
  "insufficient-evidence": {
    label: "Insufficient Evidence",
    description: "Evidence incomplete or stale.",
  },
  "conflicting-agents": {
    label: "Conflicting Agents",
    description: "Agent outputs disagree.",
  },
  "schema-invalid": { label: "Schema Invalid", description: "Response failed contract validation." },
  unavailable: { label: "Unavailable", description: "Source unavailable or access denied." },
  offline: { label: "Offline", description: "Backend unreachable." },
};

export const ExplicitState: FC<ExplicitStateProps> = ({ state, children, action }) => {
  const { label, description } = stateMap[state];
  const cls = `gm-explicit-state ${toneClass[state]}`;

  return (
    <section
      data-testid={`explicit-state-${state}`}
      aria-live="polite"
      className={cls}
    >
      <StatusBadge status={state} />
      <p className="gm-explicit-state__label">{label}</p>
      <p className="gm-explicit-state__description">{description}</p>
      {children && <div style={{ marginTop: "var(--gm-space-3)" }}>{children}</div>}
      {action && (
        <button
          onClick={action.onClick}
          className="gm-explicit-state__action"
        >
          {action.label}
        </button>
      )}
    </section>
  );
};
