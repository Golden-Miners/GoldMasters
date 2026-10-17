import { fetchAgentRuns } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function AgentRunsPage() {
  const result = await fetchAgentRuns();

  if (!result.available) {
    return <ExplicitState state="offline" />;
  }

  const { runs, status, limitations } = result.data as {
    status: string;
    runs: unknown[];
    limitations: string[];
  };

  return (
    <section aria-labelledby="agent-runs-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="agent-runs-heading">Agent Runs</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Per-node run status with explicit states. Monitoring emits no trading recommendation.
        </p>
      </header>

      <div style={{ marginBottom: "1rem" }}>
        <StatusBadge status={status} />
      </div>

      {limitations.map((l, i) => (
        <p key={i} style={{ fontSize: "0.875rem", color: "#757575", margin: "0.25rem 0" }}>
          {l}
        </p>
      ))}

      {runs.length === 0 ? (
        <ExplicitState state="empty" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
          {runs.map((run: any, index: number) => (
            <div
              key={index}
              style={{
                padding: "1rem",
                background: "#FAFAFA",
                border: "1px solid #E0E0E0",
                borderRadius: "8px",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
                <span style={{ fontWeight: 500 }}>{run.run_id ?? `run-${index}`}</span>
                <StatusBadge status={run.status ?? "unknown"} />
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.5rem", fontSize: "0.875rem" }}>
                <div>
                  <strong>Started:</strong>{" "}
                  <span style={{ fontFamily: "monospace" }}>
                    {run.started_at ? new Date(run.started_at).toLocaleString() : "—"}
                  </span>
                </div>
                <div>
                  <strong>Completed:</strong>{" "}
                  <span style={{ fontFamily: "monospace" }}>
                    {run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}
                  </span>
                </div>
                <div>
                  <strong>Retries:</strong> {run.retries ?? 0}
                </div>
                <div>
                  <strong>Bounded:</strong> {run.bounded ? "yes" : "no"}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}