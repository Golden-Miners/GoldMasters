"use client";

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
      <header className="page-header">
        <h1 id="strategy-heading" className="page-title">
          Strategy Lab
        </h1>
        <p className="page-subtitle">
          Registered strategy agents with eligibility configuration. Rule-by-rule evidence per agent.
        </p>
      </header>

      {result.agents.length === 0 ? (
        <ExplicitState state="empty" />
      ) : (
        <div className="strategy-list">
          {result.agents.map((agent: { agent_id: string; enabled: boolean; instruments: string[]; timeframes: string[]; regimes: string[]; min_bars: number }) => (
            <div className="strategy-card" key={agent.agent_id}>
              <details className="strategy-card-detail">
                <summary className="strategy-summary">
                  <StatusBadge status={agent.enabled ? "ok" : "no_setup"} />
                  <code className="strategy-id">{agent.agent_id}</code>
                  <span className="strategy-meta-text">min_bars: {agent.min_bars}</span>
                </summary>
                <div className="strategy-details">
                  <div className="strategy-row">
                    <span className="strategy-label">Instruments:</span>
                    <span className="strategy-value">{agent.instruments.join(", ")}</span>
                  </div>
                  <div className="strategy-row">
                    <span className="strategy-label">Timeframes:</span>
                    <span className="strategy-value">{agent.timeframes.join(", ")}</span>
                  </div>
                  <div className="strategy-row">
                    <span className="strategy-label">Regimes:</span>
                    <span className="strategy-value">{agent.regimes.join(", ")}</span>
                  </div>
                  <div className="strategy-actions">
                    <button className={`btn-toggle ${agent.enabled ? "enabled" : ""}`}>
                      {agent.enabled ? "Enabled" : "Disabled"}
                    </button>
                    <button className="btn-ghost">View Rules</button>
                  </div>
                </div>
              </details>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}