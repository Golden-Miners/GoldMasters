import {
  fetchHealth,
  fetchDecisions,
  fetchProviders,
  fetchMarketBars,
} from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import Link from "next/link";
import type { DecisionRecord } from "../../generated/decision";
import type { MarketBar } from "../../generated/market";

export const dynamic = "force-dynamic";

interface ProviderData {
  provider_id: string;
  status: string;
  market_open: boolean;
  terminal_build: string;
  last_bar_close_time: string | null;
  last_quote_time: string | null;
  checked_at: string;
  mt5_server_timezone: string;
}

export default async function OverviewPage() {
  const [healthResult, decisionsResult, providersResult, marketResult] =
    await Promise.all([
      fetchHealth(),
      fetchDecisions(),
      fetchProviders(),
      fetchMarketBars(),
    ]);

  if (!healthResult.available) {
    return (
      <section className="panel" aria-labelledby="overview-heading">
        <header className="page-header">
          <h1 id="overview-heading" className="page-title">
            Overview
          </h1>
          <p className="page-subtitle">
            Market snapshot · data freshness · research setups · system quality
          </p>
        </header>
        <ExplicitState state="offline" />
      </section>
    );
  }

  const { health } = healthResult;
  const decisions = decisionsResult.available ? decisionsResult.decisions : [];
  const providersData =
    providersResult.available ? (providersResult.data as ProviderData) : null;
  const bars = marketResult.available ? marketResult.bars : [];
  const recentDecisions = decisions.slice(0, 5);

  return (
    <section aria-labelledby="overview-heading">
      <header className="page-header">
        <h1 id="overview-heading" className="page-title">Overview</h1>
        <p className="page-subtitle">
          Market snapshot · data freshness · research setups · system quality
        </p>
      </header>

      <section className="panel" aria-labelledby="market-data-heading">
        <h2 id="market-data-heading" className="section-heading">
          Market Data
        </h2>
        <div className="controls-bar">
          <div className="control-group">
            <label className="control-label">Instrument</label>
            <span className="num">{bars[0]?.instrument_id ?? "—"}</span>
          </div>
          <div className="control-group">
            <label className="control-label">Timeframe</label>
            <span className="num">{bars[0]?.timeframe ?? "—"}</span>
          </div>
          <div className="control-group">
            <label className="control-label">Provider</label>
            <span className="num">{bars[0]?.provider_id ?? "—"}</span>
          </div>
          <div className="control-group">
            <label className="control-label">Bars</label>
            <span className="num">{bars.length}</span>
          </div>
          <div className="control-group">
            <label className="control-label">Quality</label>
            <span className="status-dd">
              {bars.length > 0 ? (
                <StatusBadge status={bars[0].quality_status} />
              ) : (
                <span className="gm-badge gm-badge-blocked">unavailable</span>
              )}
            </span>
          </div>
          <div className="control-group">
            <label className="control-label">Last Retrieved</label>
            <span className="num">
              {bars[0]?.retrieved_at
                ? new Date(bars[0].retrieved_at).toLocaleString()
                : "—"}
            </span>
          </div>
        </div>
        <table className="chart-table">
          <caption>Most recent bars (accessible table)</caption>
          <thead>
            <tr>
              <th>Open Time</th>
              <th className="num-col">Open</th>
              <th className="num-col">High</th>
              <th className="num-col">Low</th>
              <th className="num-col">Close</th>
              <th className="num-col">Volume</th>
            </tr>
          </thead>
          <tbody>
            {bars.slice(0, 10).map((bar: MarketBar) => (
              <tr key={bar.bar_open_time}>
                <td className="num">
                  {new Date(bar.bar_open_time).toLocaleString()}
                </td>
                <td className="num-col">{bar.open}</td>
                <td className="num-col">{bar.high}</td>
                <td className="num-col">{bar.low}</td>
                <td className="num-col">{bar.close}</td>
                <td className="num-col">{bar.volume ?? "n/a"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="panel" aria-labelledby="research-setups-heading">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "var(--gm-space-3)" }}>
          <h2 id="research-setups-heading" className="section-heading">
            Research Setups
          </h2>
          <Link href="/decision" style={{ fontSize: "var(--gm-text-sm)", color: "var(--gm-accent)" }}>
            View All &rarr;
          </Link>
        </div>
        {decisionsResult.available ? (
          recentDecisions.length === 0 ? (
            <ExplicitState state="empty" />
          ) : (
            <div className="recent-list">
              {recentDecisions.map((decision: DecisionRecord) => (
                <Link
                  key={decision.decision_id}
                  href={`/decision?id=${decision.decision_id}`}
                  className="recent-item"
                >
                  <div className="recent-left">
                    <StatusBadge status={decision.decision} />
                    <span className="num">{decision.instrument_id}</span>
                    <span style={{ fontSize: "var(--gm-text-sm)", color: "var(--gm-text-secondary)" }}>
                      {decision.timeframe}
                    </span>
                    <span style={{ fontSize: "var(--gm-text-xs)", color: "var(--gm-text-muted)" }}>
                      {decision.strategy_id}@{decision.strategy_version}
                    </span>
                  </div>
                  <time dateTime={decision.created_at} className="recent-time">
                    {new Date(decision.created_at).toLocaleString()}
                  </time>
                </Link>
              ))}
            </div>
          )
        ) : (
          <ExplicitState state="unavailable">
            <p>
              Research setups unavailable — decisions database not reachable
              ({decisionsResult.reason}).
            </p>
          </ExplicitState>
        )}
      </section>

      <section className="panel" aria-labelledby="system-quality-heading">
        <h2 id="system-quality-heading" className="section-heading">
          System &amp; Data Quality
        </h2>
        <div className="status-grid">
          <div className="status-card">
            <span className="status-dt">Backend Status</span>
            <span className="status-dd">{health.status}</span>
          </div>
          <div className="status-card">
            <span className="status-dt">Backend Version</span>
            <span className="status-dd">{health.version}</span>
          </div>
          <div className="status-card">
            <span className="status-dt">Contract Schema</span>
            <span className="status-dd">{health.contract_schema_version}</span>
          </div>
          <div className="status-card">
            <span className="status-dt">Config Hash</span>
            <span className="status-dd num">{health.config_hash.slice(0, 12)}…</span>
          </div>
          <div className="status-card">
            <span className="status-dt">Database</span>
            <span className="status-dd">
              <StatusBadge status={health.database.reachable ? "ok" : "unavailable"} />
            </span>
          </div>
          <div className="status-card">
            <span className="status-dt">Provider</span>
            <span className="status-dd">
              {providersData ? (
                <StatusBadge status={(providersData as ProviderData).status ?? "unavailable"} />
              ) : (
                <span className="gm-badge gm-badge-blocked">unavailable</span>
              )}
            </span>
          </div>
          <div className="status-card">
            <span className="status-dt">Market Data</span>
            <span className="status-dd">
              {bars.length > 0 ? (
                <span className="gm-badge gm-badge-valid">receiving</span>
              ) : (
                <span className="gm-badge gm-badge-blocked">not connected</span>
              )}
            </span>
          </div>
        </div>
        {providersData && providersData.provider_id ? (
          <div style={{ marginTop: "var(--gm-space-3)" }}>
            <span className="text-muted">
              Provider: {providersData.provider_id} &bull; Server Timezone:{" "}
              {providersData.mt5_server_timezone ?? "not set"} &bull; Last Checked:{" "}
              {new Date(providersData.checked_at).toLocaleString()}
            </span>
          </div>
        ) : (
          <div style={{ marginTop: "var(--gm-space-3)" }}>
            <span className="text-muted">Provider: not connected</span>
          </div>
        )}
      </section>
    </section>
  );
}