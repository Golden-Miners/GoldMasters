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
 * Uses design tokens from @/styles/design-tokens.css (quant terminal: cyan/teal on graphite).
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

    // QualityStatus enum
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

  // Tone → CSS class mapping (dark theme, design tokens)
  const toneClass: Record<StatusTone, string> = {
    valid: "gm-badge-valid",
    warning: "gm-badge-warning",
    blocked: "gm-badge-blocked",
    neutral: "gm-badge-neutral",
  };

  const cls = toneClass[entry.tone];

  return (
    <span
      data-testid={`badge-${status}`}
      aria-label={`${entry.label} (${status})`}
      className={`gm-badge ${cls}`}
    >
      {entry.label}
    </span>
  );
};
