import { fetchBacktests } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import type { BacktestRecord } from "../../generated/backtest";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export const dynamic = "force-dynamic";

export default async function BacktestPage() {
  const result = await fetchBacktests();

  if (!result.available) {
    return <ExplicitState state="offline" />;
  }

  const records = result.records;

  if (records.length === 0) {
    return (
      <section aria-labelledby="backtest-heading">
        <header style={{ marginBottom: "1.5rem" }}>
          <h1 id="backtest-heading">Backtest Results</h1>
          <p style={{ color: "#616161", marginTop: "0.25rem" }}>
            Reproducible, cost-aware backtests. Metrics carry placeholder-cost marker (D-6.1).
          </p>
        </header>
        <ExplicitState state="empty" />
      </section>
    );
  }

  return (
    <section aria-labelledby="backtest-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="backtest-heading">Backtest Results</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Reproducible, cost-aware backtests. Every metric definition carries "placeholder per D-6.1, not authoritative".
        </p>
      </header>

      {records.map((record: BacktestRecord) => (
        <section key={record.backtest_run_id} aria-labelledby={`backtest-${record.backtest_run_id}`} style={{ marginBottom: "2rem" }}>
          <h2 id={`backtest-${record.backtest_run_id}`} style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
            <StatusBadge status={record.status} />
            <span style={{ marginLeft: "0.5rem", fontFamily: "monospace", fontSize: "0.875rem" }}>
              {record.strategy_id}@{record.strategy_version}
            </span>
            <span style={{ marginLeft: "1rem", fontSize: "0.875rem", color: "#616161" }}>
              {record.instrument_id} {record.timeframe}
            </span>
          </h2>

          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(250px, 1fr))", gap: "1rem", marginBottom: "1rem" }}>
            {(record.metrics ?? []).map((metric) => (
              <div key={metric.name} style={{ padding: "0.75rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "6px" }}>
                <div style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase", marginBottom: "0.25rem" }}>
                  {metric.name}
                </div>
                <div style={{ fontSize: "1.25rem", fontWeight: 600, fontFamily: "monospace" }}>
                  {metric.value !== null ? String(metric.value) : "null"}
                </div>
                <div style={{ fontSize: "0.7rem", color: "#9E9E9E", marginTop: "0.25rem" }}>
                  sample: {metric.sample_size}
                </div>
                <div style={{ fontSize: "0.65rem", color: "#B71C1C", marginTop: "0.25rem" }}>
                  {metric.definition}
                </div>
              </div>
            ))}
          </div>

          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem", marginBottom: "1rem" }}>
            <caption style={{ textAlign: "left", marginBottom: "0.5rem", fontWeight: 500, fontSize: "0.875rem" }}>
              Metrics data table (accessible alternative)
            </caption>
            <thead>
              <tr style={{ background: "#F5F5F5" }}>
                <th style={{ padding: "0.5rem", textAlign: "left", borderBottom: "1px solid #E0E0E0" }}>Metric</th>
                <th style={{ padding: "0.5rem", textAlign: "right", borderBottom: "1px solid #E0E0E0" }}>Value</th>
                <th style={{ padding: "0.5rem", textAlign: "center", borderBottom: "1px solid #E0E0E0" }}>Sample</th>
                <th style={{ padding: "0.5rem", textAlign: "left", borderBottom: "1px solid #E0E0E0" }}>Definition</th>
              </tr>
            </thead>
            <tbody>
              {(record.metrics ?? []).map((metric) => (
                <tr key={metric.name} style={{ borderBottom: "1px solid #F0F0F0" }}>
                  <td style={{ padding: "0.5rem", fontWeight: 500 }}>{metric.name}</td>
                  <td style={{ padding: "0.5rem", textAlign: "right", fontFamily: "monospace" }}>
                    {metric.value !== null ? String(metric.value) : "null"}
                  </td>
                  <td style={{ padding: "0.5rem", textAlign: "center" }}>{metric.sample_size}</td>
                  <td style={{ padding: "0.5rem", fontSize: "0.7rem", color: "#B71C1C" }}>
                    {metric.definition}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      ))}
    </section>
  );
}