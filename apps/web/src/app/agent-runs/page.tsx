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
    <section className="panel" aria-labelledby="agent-runs-heading">
      <header className="page-header">
        <h1 id="agent-runs-heading" className="page-title">Agent Runs</h1>
        <p className="page-subtitle">
          Per-node run status with explicit states. Monitoring emits no trading recommendation.
        </p>
      </header>

      <div style={{ marginBottom: "var(--gm-space-3)" }}>
        <StatusBadge status={status} />
      </div>

      {limitations.map((l, i) => (
        <p key={i} className="text-muted" style={{ margin: "0" }}>
          {l}
        </p>
      ))}

      {runs.length === 0 ? (
        <ExplicitState state="empty" />
      ) : (
        <div className="run-list">
          {runs.map((run: any, index: number) => (
            <div className="run-item" key={index}>
              <div className="run-head">
                <span className="run-id">{run.run_id ?? `run-${index}`}</span>
                <StatusBadge status={run.status ?? "unknown"} />
              </div>
              <div className="run-details">
                <div className="run-row">
                  <span className="run-label">Started:</span>
                  <span className="run-value">{run.started_at ? new Date(run.started_at).toLocaleString() : "—"}</span>
                </div>
                <div className="run-row">
                  <span className="run-label">Completed:</span>
                  <span className="run-value">{run.completed_at ? new Date(run.completed_at).toLocaleString() : "—"}</span>
                </div>
                <div className="run-row">
                  <span className="run-label">Retries:</span>
                  <span className="run-value">{run.retries ?? 0}</span>
                </div>
                <div className="run-row">
                  <span className="run-label">Bounded:</span>
                  <span className="run-value">{run.bounded ? "yes" : "no"}</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
