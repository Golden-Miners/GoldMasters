import { fetchHealth, fetchDecisions, fetchProviders } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import Link from "next/link";
import type { DecisionRecord } from "../../generated/decision";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  const [healthResult, decisionsResult, providersResult] = await Promise.all([
    fetchHealth(),
    fetchDecisions(),
    fetchProviders(),
  ]);

  if (!healthResult.available) {
    return (
      <ExplicitState state="offline">
        <p>Backend unreachable: {healthResult.reason}</p>
      </ExplicitState>
    );
  }

  const { health } = healthResult;
  const decisions = decisionsResult.available ? decisionsResult.decisions : [];
  const providersData = providersResult.available ? providersResult.data : null;

  const recentDecisions = decisions.slice(0, 5);

  return (
    <section aria-labelledby="overview-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="overview-heading">Overview</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          System status, provider health, and recent decisions at a glance.
        </p>
      </header>

      <section aria-labelledby="system-status-heading" style={{ marginBottom: "1.5rem" }}>
        <h2 id="system-status-heading" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          System Status
        </h2>
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Backend Status</dt>
            <dd style={{ fontWeight: 500 }}>{health.status}</dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Backend Version</dt>
            <dd style={{ fontWeight: 500 }}>{health.version}</dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Contract Schema</dt>
            <dd style={{ fontWeight: 500 }}>{health.contract_schema_version}</dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Config Hash</dt>
            <dd style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.875rem" }}>{health.config_hash.slice(0, 12)}…</dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Database</dt>
            <dd style={{ fontWeight: 500 }}>
              <StatusBadge status={health.database.reachable ? "ok" : "unavailable"} />
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="provider-status-heading" style={{ marginBottom: "1.5rem" }}>
        <h2 id="provider-status-heading" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          Provider Status
        </h2>
        {providersData ? (
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0", minWidth: "200px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Provider ID</dt>
              <dd style={{ fontWeight: 500 }}>{(providersData as any).provider_id ?? "unknown"}</dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0", minWidth: "200px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Status</dt>
              <dd style={{ fontWeight: 500 }}>
                <StatusBadge status={(providersData as any).status ?? "unavailable"} />
              </dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0", minWidth: "200px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Market Open</dt>
              <dd style={{ fontWeight: 500 }}>{(providersData as any).market_open === true ? "yes" : "no"}</dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "0.75rem", background: "#F5F5F5", borderRadius: "6px", border: "1px solid #E0E0E0", minWidth: "200px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Terminal Build</dt>
              <dd style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.875rem" }}>{(providersData as any).terminal_build ?? "unknown"}</dd>
            </div>
          </div>
        ) : (
          <ExplicitState state="unavailable" />
        )}
      </section>

      <section aria-labelledby="recent-decisions-heading">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "0.75rem" }}>
          <h2 id="recent-decisions-heading" style={{ fontSize: "1.125rem", margin: 0 }}>
            Recent Decisions
          </h2>
          <Link href="/decision" style={{ fontSize: "0.875rem", color: "#1976D2" }}>
            View All →
          </Link>
        </div>
        {recentDecisions.length === 0 ? (
          <ExplicitState state="empty" />
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
            {recentDecisions.map((decision: DecisionRecord) => (
              <Link
                key={decision.decision_id}
                href={`/decision?id=${decision.decision_id}`}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "0.75rem 1rem",
                  background: "#FAFAFA",
                  border: "1px solid #E0E0E0",
                  borderRadius: "6px",
                  textDecoration: "none",
                  color: "inherit",
                  transition: "background 0.15s, border-color 0.15s",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "0.75rem" }}>
                  <StatusBadge status={decision.decision} />
                  <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
                    {decision.instrument_id}
                  </span>
                  <span style={{ fontSize: "0.875rem", color: "#616161" }}>
                    {decision.timeframe}
                  </span>
                  <span style={{ fontSize: "0.75rem", color: "#757575" }}>
                    {decision.strategy_id}@{decision.strategy_version}
                  </span>
                </div>
                <time dateTime={decision.created_at} style={{ fontSize: "0.75rem", color: "#757575", fontFamily: "monospace" }}>
                  {new Date(decision.created_at).toLocaleString()}
                </time>
              </Link>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}