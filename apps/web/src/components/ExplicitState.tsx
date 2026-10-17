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

const stateMap: Record<ExplicitState, { label: string; description: string; tone: "neutral" | "warning" | "blocked" }> = {
  empty: { label: "Empty", description: "No data available.", tone: "neutral" },
  loading: { label: "Loading…", description: "Fetching live state.", tone: "neutral" },
  degraded: { label: "Degraded", description: "Partial data; some sources unavailable.", tone: "warning" },
  stale: { label: "Stale", description: "Data freshness exceeded threshold.", tone: "warning" },
  "no-setup": { label: "No Setup", description: "No qualifying setup found.", tone: "neutral" },
  "insufficient-evidence": { label: "Insufficient Evidence", description: "Evidence incomplete or stale.", tone: "warning" },
  "conflicting-agents": { label: "Conflicting Agents", description: "Agent outputs disagree.", tone: "warning" },
  "schema-invalid": { label: "Schema Invalid", description: "Response failed contract validation.", tone: "blocked" },
  unavailable: { label: "Unavailable", description: "Source unavailable or access denied.", tone: "blocked" },
  offline: { label: "Offline", description: "Backend unreachable.", tone: "blocked" },
};

export const ExplicitState: FC<ExplicitStateProps> = ({ state, children, action }) => {
  const { label, description, tone } = stateMap[state];

  const toneStyles: Record<"neutral" | "warning" | "blocked", React.CSSProperties> = {
    neutral: { backgroundColor: "#F5F5F5", color: "#424242", borderColor: "#BDBDBD" },
    warning: { backgroundColor: "#FFF3E0", color: "#E65100", borderColor: "#FFB74D" },
    blocked: { backgroundColor: "#FBE9E7", color: "#B71C1C", borderColor: "#EF9A9A" },
  };

  return (
    <section
      data-testid={`explicit-state-${state}`}
      aria-live="polite"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "1.5rem",
        borderRadius: "8px",
        border: "1px solid",
        backgroundColor: toneStyles[tone].backgroundColor,
        color: toneStyles[tone].color,
        borderColor: toneStyles[tone].borderColor,
        gap: "0.5rem",
      }}
    >
      <StatusBadge status={state} />
      <p style={{ margin: 0, fontWeight: 500 }}>{label}</p>
      <p style={{ margin: 0, fontSize: "0.875rem", opacity: 0.8 }}>{description}</p>
      {children && <div style={{ marginTop: "0.5rem" }}>{children}</div>}
      {action && (
        <button
          onClick={action.onClick}
          style={{
            marginTop: "0.75rem",
            padding: "0.5rem 1rem",
            borderRadius: "4px",
            border: "1px solid currentColor",
            background: "transparent",
            color: "inherit",
            cursor: "pointer",
            font: "inherit",
          }}
        >
          {action.label}
        </button>
      )}
    </section>
  );
};