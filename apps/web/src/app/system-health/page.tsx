import { fetchHealth } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function SystemHealthPage() {
  const result = await fetchHealth();

  if (!result.available) {
    return (
      <section className="panel" aria-labelledby="system-health-heading">
        <header className="page-header">
          <h1 id="system-health-heading" className="page-title">
            System Health
          </h1>
          <p className="page-subtitle">
            Five-field health surface plus bounded provider probe.
          </p>
        </header>
        <ExplicitState state="offline" />
      </section>
    );
  }

  const { health } = result;

  return (
    <section className="panel" aria-labelledby="system-health-heading">
      <header className="page-header">
        <h1 id="system-health-heading" className="page-title">System Health</h1>
        <p className="page-subtitle">
          Five-field health surface plus bounded provider probe. Database reachable,
          provider status, correlation-ID presence.
        </p>
      </header>

      <section aria-labelledby="core-health" style={{ marginBottom: "var(--gm-space-8)" }}>
        <h2 id="core-health" className="section-heading">Core Health</h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "var(--gm-space-3)" }}>
          <div className="health-card">
            <span className="health-dt">Status</span>
            <span className="health-dd"><StatusBadge status={health.status} /></span>
          </div>
          <div className="health-card">
            <span className="health-dt">Version</span>
            <span className="health-dd num">{health.version}</span>
          </div>
          <div className="health-card">
            <span className="health-dt">Contract Schema</span>
            <span className="health-dd">{health.contract_schema_version}</span>
          </div>
          <div className="health-card">
            <span className="health-dt">Config Hash</span>
            <span className="health-dd num">{health.config_hash}</span>
          </div>
          <div className="health-card">
            <span className="health-dt">Database</span>
            <span className="health-dd"><StatusBadge status={health.database.reachable ? "ok" : "unavailable"} /></span>
          </div>
          <div className="health-card">
            <span className="health-dt">Provider</span>
            <span className="health-dd">
              {health.provider && typeof health.provider === "object" ? (
                <StatusBadge status={(health.provider as any).status ?? "unavailable"} />
              ) : (
                <span className="gm-badge gm-badge-blocked">unavailable</span>
              )}
            </span>
          </div>
          <div className="health-card">
            <span className="health-dt">Market Data</span>
            <span className="status-dd">
              {health.provider && typeof health.provider === "object" ? (
                <span className="gm-badge gm-badge-valid">receiving</span>
              ) : (
                <span className="gm-badge gm-badge-blocked">not connected</span>
              )}
            </span>
          </div>
        </div>
        <div style={{ marginTop: "var(--gm-space-3)" }}>
          {health.provider && typeof health.provider === "object" ? (
            <span className="text-muted">
              Provider: {(health.provider as any).provider_id} · Server Timezone:{" "}
              {(health.provider as any).mt5_server_timezone ?? "not set"} · Last Checked:{" "}
              {new Date((health.provider as any).checked_at).toLocaleString()}
            </span>
          ) : (
            <span className="text-muted">Provider: not connected</span>
          )}
        </div>
      </section>
    </section>
  );
}
