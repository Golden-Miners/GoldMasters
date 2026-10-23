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
    <section className="panel" aria-labelledby="settings-heading">
      <header className="page-header">
        <h1 id="settings-heading" className="page-title">
          Settings / Model Health
        </h1>
        <p className="page-subtitle">
          Effective configuration (non-secret) and Ollama model discovery status.
        </p>
      </header>

      <section aria-labelledby="model-health" style={{ marginBottom: "var(--gm-space-8)" }}>
        <h2 id="model-health" className="section-heading">Model Health</h2>
        {modelResult.available ? (
          <>
            <div className="model-card">
              <div className="model-row">
                <span className="model-label">Status</span>
                <span className="model-value">
                  <StatusBadge status={(modelResult.data as any).status} />
                </span>
              </div>
              <div className="model-row">
                <span className="model-label">Endpoint</span>
                <span className="model-value num">
                  {(modelResult.data as any).endpoint}
                </span>
              </div>
              <div className="model-row">
                <span className="model-label">Expected Model</span>
                <span className="model-value num">
                  {(modelResult.data as any).expected_model ?? "not configured"}
                </span>
              </div>
            </div>
            {modelResult.data?.limitations && (
              <div className="model-limitation">
                {(modelResult.data as any).limitations.join("; ")}
              </div>
            )}
          </>
        ) : (
          <ExplicitState state="offline" />
        )}
      </section>

      <section aria-labelledby="effective-config">
        <h2 id="effective-config" className="section-heading">
          Effective Configuration (non-secret)
        </h2>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "var(--gm-space-3)" }}>
          {Object.entries(config).map(([key, value]) => (
            <div key={key} className="config-item">
              <div className="config-key">{key}</div>
              <div className="config-value">
                {typeof value === "object" ? JSON.stringify(value, null, 2) : String(value)}
              </div>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}
