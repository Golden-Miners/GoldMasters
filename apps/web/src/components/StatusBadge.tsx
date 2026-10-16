import type { ReactNode } from "react";

type Tone = "valid" | "warning" | "blocked" | "neutral";

interface BadgeEntry {
  label: string;
  tone: Tone;
  icon: string;
}

const ENUM_MAP: Record<string, BadgeEntry> = {
  // Decision
  TRADE: { label: "Trade", tone: "valid", icon: "▲" },
  NO_TRADE: { label: "No trade", tone: "neutral", icon: "○" },
  INSUFFICIENT_DATA: { label: "Insufficient data", tone: "warning", icon: "⚠" },
  // AgentRunStatus
  queued: { label: "Queued", tone: "neutral", icon: "⏳" },
  running: { label: "Running", tone: "neutral", icon: "▶" },
  ok: { label: "OK", tone: "valid", icon: "✓" },
  no_setup: { label: "No setup", tone: "warning", icon: "⚠" },
  insufficient_data: { label: "Insufficient data", tone: "warning", icon: "⚠" },
  skipped: { label: "Skipped", tone: "neutral", icon: "⊘" },
  error: { label: "Error", tone: "blocked", icon: "✕" },
  timed_out: { label: "Timed out", tone: "blocked", icon: "⏱" },
  cancelled: { label: "Cancelled", tone: "neutral", icon: "⊘" },
  // EvidenceStatus
  valid: { label: "Valid", tone: "valid", icon: "✓" },
  stale: { label: "Stale", tone: "warning", icon: "⚠" },
  missing: { label: "Missing", tone: "blocked", icon: "✕" },
  conflicted: { label: "Conflicted", tone: "blocked", icon: "⚠" },
  invalid: { label: "Invalid", tone: "blocked", icon: "✕" },
  unavailable: { label: "Unavailable", tone: "blocked", icon: "⊘" },
  // QualityStatus
  duplicate: { label: "Duplicate", tone: "warning", icon: "⚠" },
  gap: { label: "Gap", tone: "warning", icon: "⚠" },
  malformed: { label: "Malformed", tone: "blocked", icon: "✕" },
  disconnected: { label: "Disconnected", tone: "blocked", icon: "⊘" },
  "missing-history": { label: "Missing history", tone: "blocked", icon: "⚠" },
  unsupported: { label: "Unsupported", tone: "blocked", icon: "⊘" },
  not_evaluated: { label: "Not evaluated", tone: "neutral", icon: "○" },
  // Direction
  long: { label: "Long", tone: "valid", icon: "▲" },
  short: { label: "Short", tone: "warning", icon: "▼" },
  neutral: { label: "Neutral", tone: "neutral", icon: "○" },
  unknown: { label: "Unknown", tone: "neutral", icon: "?" },
};

const TONE_CLASS: Record<Tone, string> = {
  valid: "badge-valid",
  warning: "badge-warning",
  blocked: "badge-blocked",
  neutral: "badge-neutral",
};

export function StatusBadge({ status }: { status: string }) {
  const entry = ENUM_MAP[status] ?? { label: status, tone: "neutral" as Tone, icon: "?" };
  return (
    <span
      className={`badge ${TONE_CLASS[entry.tone]}`}
      data-testid={`badge-${status}`}
      aria-label={`${entry.label} (${status})`}
    >
      <span aria-hidden="true">{entry.icon}</span> {entry.label}
    </span>
  );
}
