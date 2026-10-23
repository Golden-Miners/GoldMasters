import { fetchBacktests } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import type { BacktestRecord } from "../../generated/backtest";

export const dynamic = "force-dynamic";

export default async function BacktestPage() {
  const result = await fetchBacktests();

  if (!result.available) {
    return <ExplicitState state="offline" />;
  }

  const records = result.records;

  if (records.length === 0) {
    return (
      <section className="panel" aria-labelledby="backtest-heading">
        <header className="page-header">
          <h1 id="backtest-heading" className="page-title">
            Backtest Results
          </h1>
          <p className="page-subtitle">
            Reproducible, cost-aware backtests. Metrics carry placeholder-cost marker (D-6.1).
          </p>
        </header>
        <ExplicitState state="empty" />
      </section>
    );
  }

  return (
    <section className="panel" aria-labelledby="backtest-heading">
      <header className="page-header">
        <h1 id="backtest-heading" className="page-title">
          Backtest Results
        </h1>
        <p className="page-subtitle">
          Reproducible, cost-aware backtests. Every metric definition carries
          "placeholder per D-6.1, not authoritative".
        </p>
      </header>

      {records.map((record: BacktestRecord) => (
        <section
          key={record.backtest_run_id}
          aria-labelledby={`backtest-${record.backtest_run_id}`}
          className="backtest-card"
        >
          <h2 id={`backtest-${record.backtest_run_id}`} className="section-heading">
            <span className={`gm-badge gm-badge-${record.status === "valid" ? "valid" : record.status === "stale" ? "warning" : "neutral"}`}>{record.status}</span>
            <span className="num" style={{ marginLeft: "var(--gm-space-2)", fontSize: "var(--gm-text-sm)" }}>
              {record.strategy_id}@{record.strategy_version}
            </span>
            <span className="text-muted" style={{ marginLeft: "var(--gm-space-4)", fontSize: "var(--gm-text-sm)" }}>
              {record.instrument_id} {record.timeframe}
            </span>
          </h2>

          <div className="metric-grid">
            {(record.metrics ?? []).map((metric) => (
              <div key={metric.name} className="metric-card">
                <div className="metric-name">{metric.name}</div>
                <div className="metric-value num">
                  {metric.value !== null ? String(metric.value) : "null"}
                </div>
                <div className="metric-sample">sample: {metric.sample_size}</div>
                <div className="metric-definition">{metric.definition}</div>
              </div>
            ))}
          </div>

          <table className="chart-table">
            <caption>Metrics data table (accessible alternative)</caption>
            <thead>
              <tr>
                <th>Metric</th>
                <th className="num-col">Value</th>
                <th className="num-col">Sample</th>
                <th>Definition</th>
              </tr>
            </thead>
            <tbody>
              {(record.metrics ?? []).map((metric) => (
                <tr key={metric.name}>
                  <td style={{ fontWeight: 500 }}>{metric.name}</td>
                  <td className="num-col">
                    {metric.value !== null ? String(metric.value) : "null"}
                  </td>
                  <td className="num-col">{metric.sample_size}</td>
                  <td className="text-muted">{metric.definition}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </section>
  );
}
