import { fetchHealth } from "../lib/api";

export const dynamic = "force-dynamic";

export default async function HealthPage() {
  const result = await fetchHealth();

  if (!result.available) {
    return (
      <main>
        <h1>GoldMasters Research Console</h1>
        <p role="status">API unavailable: {result.reason}</p>
        <p>No market data is shown because the backend cannot be reached.</p>
      </main>
    );
  }

  const { health } = result;
  return (
    <main>
      <h1>GoldMasters Research Console</h1>
      <dl>
        <dt>Backend status</dt>
        <dd>{health.status}</dd>
        <dt>Backend version</dt>
        <dd>{health.version}</dd>
        <dt>Contract schema version</dt>
        <dd>{health.contract_schema_version}</dd>
        <dt>Effective-config hash</dt>
        <dd>{health.config_hash}</dd>
        <dt>Database reachable</dt>
        <dd>{health.database.reachable ? "yes" : "no"}</dd>
      </dl>
    </main>
  );
}
