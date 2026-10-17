import { fetchDecisions } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import Link from "next/link";
import type { DecisionRecord } from "../../generated/decision";

export const dynamic = "force-dynamic";

export default async function DecisionPage() {
  const decisionsResult = await fetchDecisions();

  if (!decisionsResult.available) {
    return <ExplicitState state="offline" />;
  }

  const decisions = decisionsResult.decisions;

  if (decisions.length === 0) {
    return <ExplicitState state="empty" />;
  }

  return (
    <section aria-labelledby="decision-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="decision-heading">Decision Detail</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Evidence-ledger view of a qualified research candidate. No trade execution.
        </p>
      </header>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {decisions.map((decision: DecisionRecord) => (
          <Link
            key={decision.decision_id}
            href={`/decision?id=${decision.decision_id}`}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "1rem 1.25rem",
              background: "#FAFAFA",
              border: "1px solid #E0E0E0",
              borderRadius: "8px",
              textDecoration: "none",
              color: "inherit",
              transition: "background 0.15s, border-color 0.15s",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "1rem", flexWrap: "wrap" }}>
              <StatusBadge status={decision.decision} />
              <span style={{ fontFamily: "monospace", fontSize: "0.875rem", fontWeight: 500 }}>
                {decision.instrument_id}
              </span>
              <span style={{ fontSize: "0.875rem", color: "#616161" }}>
                {decision.timeframe}
              </span>
              <span style={{ fontSize: "0.75rem", color: "#757575" }}>
                {decision.strategy_id}@{decision.strategy_version}
              </span>
              {decision.direction && <StatusBadge status={decision.direction} />}
              <time dateTime={decision.created_at} style={{ fontSize: "0.75rem", color: "#757575", fontFamily: "monospace" }}>
                {new Date(decision.created_at).toLocaleString()}
              </time>
            </div>
            <span style={{ fontSize: "0.875rem", color: "#1976D2", fontWeight: 500 }}>
              Open Evidence →
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}