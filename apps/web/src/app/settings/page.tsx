import { fetchSettings, fetchModelHealth } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function SettingsPage() {
  const [settingsResult, modelResult] = await Promise.all([
    fetchSettings(),
    fetchModelHealth(),
  ]);

  if (!settingsResult.available) {
    return <ExplicitState state="offline" />;
  }

  const config = settingsResult.config;

  return (
    <section aria-labelledby="settings-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="settings-heading">Settings / Model Health</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Effective configuration (non-secret) and Ollama model discovery status.
        </p>
      </header>

      <section aria-labelledby="model-health" style={{ marginBottom: "2rem" }}>
        <h2 id="model-health" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          Model Health
        </h2>
        {modelResult.available ? (
          <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", alignItems: "center" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px", minWidth: "200px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Status</span>
                <StatusBadge status={(modelResult.data as any).status} />
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Endpoint</span>
                <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>{(modelResult.data as any).endpoint}</span>
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
                <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Expected Model</span>
                <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>{(modelResult.data as any).expected_model ?? "not configured"}</span>
              </div>
            </div>
            <div style={{ padding: "0.75rem", background: "#FFF3E0", border: "1px solid #FFB74D", borderRadius: "6px", fontSize: "0.875rem", color: "#E65100" }}>
              {(modelResult.data as any).limitations?.join("; ")}
            </div>
          </div>
        ) : (
          <ExplicitState state="offline" />
        )}
      </section>

      <section aria-labelledby="effective-config">
        <h2 id="effective-config" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          Effective Configuration (non-secret)
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "0.75rem" }}>
          {Object.entries(config).map(([key, value]) => (
            <div key={key} style={{ padding: "0.75rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "6px" }}>
              <div style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase", fontWeight: 500, marginBottom: "0.25rem" }}>
                {key}
              </div>
              <div style={{ fontFamily: "monospace", fontSize: "0.875rem", wordBreak: "break-all" }}>
                {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}
              </div>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}