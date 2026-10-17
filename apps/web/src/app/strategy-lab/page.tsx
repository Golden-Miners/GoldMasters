import { fetchStrategies } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function StrategyLabPage() {
  const result = await fetchStrategies();

  if (!result.available) {
    return <ExplicitState state="offline" />;
  }

  return (
    <section aria-labelledby="strategy-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="strategy-heading">Strategy Lab</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Registered strategy agents with eligibility configuration. Rule-by-rule evidence per agent.
        </p>
      </header>

      {result.agents.length === 0 ? (
        <ExplicitState state="empty" />
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "0.75rem" }}>
          {result.agents.map((agent: { agent_id: string; enabled: boolean; instruments: string[]; timeframes: string[]; regimes: string[]; min_bars: number }) => (
            <details
              key={agent.agent_id}
              style={{
                padding: "1rem",
                background: "#FAFAFA",
                border: "1px solid #E0E0E0",
                borderRadius: "8px",
              }}
            >
              <summary style={{ cursor: "pointer", display: "flex", alignItems: "center", gap: "1rem" }}>
                <StatusBadge status={agent.enabled ? "ok" : "no_setup"} />
                <code style={{ fontSize: "0.875rem" }}>{agent.agent_id}</code>
                <span style={{ fontSize: "0.875rem", color: "#616161" }}>
                  min_bars: {agent.min_bars}
                </span>
              </summary>
              <div style={{ marginTop: "0.75rem", paddingLeft: "2rem", display: "flex", flexDirection: "column", gap: "0.5rem" }}>
                <div>
                  <strong>Instruments:</strong>{" "}
                  <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
                    {agent.instruments.join(", ")}
                  </span>
                </div>
                <div>
                  <strong>Timeframes:</strong>{" "}
                  <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
                    {agent.timeframes.join(", ")}
                  </span>
                </div>
                <div>
                  <strong>Regimes:</strong>{" "}
                  <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
                    {agent.regimes.join(", ")}
                  </span>
                </div>
              </div>
            </details>
          ))}
        </div>
      )}
    </section>
  );
}