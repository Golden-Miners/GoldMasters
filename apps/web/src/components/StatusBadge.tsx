"use client";

import type { FC } from "react";

type StatusTone = "valid" | "warning" | "blocked" | "neutral";

interface StatusBadgeProps {
  status: string;
}

/**
 * StatusBadge maps every closed enum value verbatim to a labelled badge.
 * Colour is supplementary only — never the sole carrier of meaning (WCAG 1.4.1).
 * Unknown / not_evaluated render neutral, never healthy.
 */
export const StatusBadge: FC<StatusBadgeProps> = ({ status }) => {
  const map: Record<string, { label: string; tone: StatusTone }> = {
    // Decision enum
    TRADE: { label: "TRADE", tone: "valid" },
    NO_TRADE: { label: "NO TRADE", tone: "blocked" },
    INSUFFICIENT_DATA: { label: "INSUFFICIENT DATA", tone: "warning" },

    // AgentRunStatus enum
    queued: { label: "Queued", tone: "neutral" },
    running: { label: "Running", tone: "neutral" },
    ok: { label: "OK", tone: "valid" },
    no_setup: { label: "No Setup", tone: "neutral" },
    insufficient_data: { label: "Insufficient Data", tone: "warning" },
    skipped: { label: "Skipped", tone: "neutral" },
    error: { label: "Error", tone: "blocked" },
    timed_out: { label: "Timed Out", tone: "blocked" },
    cancelled: { label: "Cancelled", tone: "neutral" },

    // EvidenceStatus enum
    valid: { label: "Valid", tone: "valid" },
    stale: { label: "Stale", tone: "warning" },
    missing: { label: "Missing", tone: "blocked" },
    conflicted: { label: "Conflicted", tone: "warning" },
    invalid: { label: "Invalid", tone: "blocked" },
    unavailable: { label: "Unavailable", tone: "blocked" },

    // QualityStatus enum (ok already exists from AgentRunStatus - same label/tone)
    duplicate: { label: "Duplicate", tone: "warning" },
    gap: { label: "Gap", tone: "warning" },
    malformed: { label: "Malformed", tone: "blocked" },
    disconnected: { label: "Disconnected", tone: "blocked" },
    "missing-history": { label: "Missing History", tone: "blocked" },
    unsupported: { label: "Unsupported", tone: "blocked" },
    not_evaluated: { label: "Not Evaluated", tone: "neutral" },

    // Direction enum
    long: { label: "Long", tone: "valid" },
    short: { label: "Short", tone: "valid" },
    neutral: { label: "Neutral", tone: "neutral" },
    unknown: { label: "Unknown", tone: "neutral" },
  };

  const entry = map[status] ?? { label: status, tone: "neutral" };

  const toneStyles: Record<StatusTone, React.CSSProperties> = {
    valid: { backgroundColor: "#E8F5E9", color: "#1B5E20", borderColor: "#81C784" },
    warning: { backgroundColor: "#FFF3E0", color: "#E65100", borderColor: "#FFB74D" },
    blocked: { backgroundColor: "#FBE9E7", color: "#B71C1C", borderColor: "#EF9A9A" },
    neutral: { backgroundColor: "#ECEFF1", color: "#37474F", borderColor: "#B0BEC5" },
  };

  const style = toneStyles[entry.tone];

  return (
    <span
      data-testid={`badge-${status}`}
      aria-label={`${entry.label} (${status})`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: "4px",
        fontSize: "0.75rem",
        fontWeight: 500,
        border: "1px solid",
        ...style,
      }}
    >
      {entry.label}
    </span>
  );
};