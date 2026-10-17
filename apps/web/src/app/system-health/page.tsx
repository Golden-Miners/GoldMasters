import { fetchHealth } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function SystemHealthPage() {
  const result = await fetchHealth();

  if (!result.available) {
    return (
      <section aria-labelledby="system-health-heading">
        <header style={{ marginBottom: "1.5rem" }}>
          <h1 id="system-health-heading">System Health</h1>
          <p style={{ color: "#616161", marginTop: "0.25rem" }}>
            Five-field health surface plus bounded provider probe.
          </p>
        </header>
        <ExplicitState state="offline" />
      </section>
    );
  }

  const { health } = result;

  return (
    <section aria-labelledby="system-health-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="system-health-heading">System Health</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Five-field health surface plus bounded provider probe. Database reachable, provider status, correlation-id presence.
        </p>
      </header>

      <section aria-labelledby="core-health" style={{ marginBottom: "2rem" }}>
        <h2 id="core-health" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          Core Health
        </h2>
        <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Status</dt>
            <dd style={{ fontWeight: 500 }}>
              <StatusBadge status={health.status} />
            </dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Version</dt>
            <dd style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.875rem" }}>{health.version}</dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Contract Schema</dt>
            <dd style={{ fontWeight: 500 }}>{health.contract_schema_version}</dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Config Hash</dt>
            <dd style={{ fontWeight: 500, fontFamily: "monospace", fontSize: "0.75rem" }}>{health.config_hash}</dd>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
            <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Database</dt>
            <dd style={{ fontWeight: 500 }}>
              <StatusBadge status={health.database.reachable ? "ok" : "unavailable"} />
            </dd>
          </div>
        </dl>
      </section>

      <section aria-labelledby="provider-probe">
        <h2 id="provider-probe" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          Provider Probe
        </h2>
        {health.provider && typeof health.provider === "object" ? (
          <dl style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: "0.75rem" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Provider ID</dt>
              <dd style={{ fontWeight: 500, fontFamily: "monospace" }}>{(health.provider as any).provider_id ?? "unknown"}</dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Status</dt>
              <dd style={{ fontWeight: 500 }}>
                <StatusBadge status={(health.provider as any).status ?? "unavailable"} />
              </dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Market Open</dt>
              <dd style={{ fontWeight: 500 }}>{(health.provider as any).market_open === true ? "yes" : "no"}</dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Terminal Build</dt>
              <dd style={{ fontWeight: 500, fontFamily: "monospace" }}>{(health.provider as any).terminal_build ?? "unknown"}</dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Last Bar Close</dt>
              <dd style={{ fontFamily: "monospace" }}>
                {(health.provider as any).last_bar_close_time ? new Date((health.provider as any).last_bar_close_time).toLocaleString() : "—"}
              </dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Last Quote</dt>
              <dd style={{ fontFamily: "monospace" }}>
                {(health.provider as any).last_quote_time ? new Date((health.provider as any).last_quote_time).toLocaleString() : "—"}
              </dd>
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px" }}>
              <dt style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Checked At</dt>
              <dd style={{ fontFamily: "monospace" }}>
                {(health.provider as any).checked_at ? new Date((health.provider as any).checked_at).toLocaleString() : "—"}
              </dd>
            </div>
          </dl>
        ) : (
          <p style={{ color: "#757575" }}>No provider data available.</p>
        )}
      </section>
    </section>
  );
}