"use client";

import { useState, useEffect } from "react";
import { fetchMarketBars } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface CandlePoint {
  t: string;
  o: number;
  h: number;
  l: number;
  c: number;
}

interface TooltipPayloadItem {
  value: number;
  name: string;
}

export default function WorkbenchPage() {
  const [state, setState] = useState<"loading" | "empty" | "stale" | "ready" | "offline">("loading");
  const [candles, setCandles] = useState<CandlePoint[]>([]);
  const [instrument, setInstrument] = useState("xauusd");
  const [timeframe, setTimeframe] = useState("H1");
  const [count, setCount] = useState(200);

  const fetchData = async () => {
    setState("loading");
    try {
      const result = await fetchMarketBars(instrument, timeframe, count);
      if (!result.available) {
        setState("offline");
        return;
      }
      if (result.bars.length === 0) {
        setState("empty");
        return;
      }
      const points = result.bars.map((bar) => ({
        t: bar.bar_close_time ?? bar.bar_open_time,
        o: Number(bar.open),
        h: Number(bar.high),
        l: Number(bar.low),
        c: Number(bar.close),
      }));
      setCandles(points);
      setState(points.length > 0 ? "ready" : "empty");
    } catch {
      setState("offline");
    }
  };

  useEffect(() => {
    fetchData();
  }, [instrument, timeframe, count]);

  if (state === "loading") return <ExplicitState state="loading" />;
  if (state === "offline") return <ExplicitState state="offline" />;
  if (state === "empty") return <ExplicitState state="empty" />;

  const tooltipFormatter: any = (value: number | undefined, name: string) => [value !== undefined ? value.toFixed(2) : "-", name];
  const tooltipLabelFormatter: any = (v: React.ReactNode) => {
    if (typeof v === "string") return new Date(v).toLocaleString();
    return String(v);
  };

  return (
    <section aria-labelledby="workbench-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="workbench-heading">Instrument Workbench</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Live price chart with accessible data table alternative.
        </p>
      </header>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label htmlFor="instrument" style={{ fontSize: "0.875rem", fontWeight: 500 }}>
            Instrument
          </label>
          <select
            id="instrument"
            value={instrument}
            onChange={(e) => setInstrument(e.target.value)}
            style={{ padding: "0.375rem 0.75rem", border: "1px solid #E0E0E0", borderRadius: "4px", fontSize: "0.875rem" }}
          >
            <option value="xauusd">XAUUSD (Gold)</option>
            <option value="xagusd">XAGUSD (Silver)</option>
            <option value="eurusd">EURUSD</option>
            <option value="gbpusd">GBPUSD</option>
            <option value="btcusd">BTCUSD</option>
            <option value="ethusd">ETHUSD</option>
            <option value="usoil">USOIL</option>
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label htmlFor="timeframe" style={{ fontSize: "0.875rem", fontWeight: 500 }}>
            Timeframe
          </label>
          <select
            id="timeframe"
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
            style={{ padding: "0.375rem 0.75rem", border: "1px solid #E0E0E0", borderRadius: "4px", fontSize: "0.875rem" }}
          >
            <option value="M1">M1</option>
            <option value="M5">M5</option>
            <option value="M15">M15</option>
            <option value="M30">M30</option>
            <option value="H1">H1</option>
            <option value="H4">H4</option>
            <option value="D1">D1</option>
          </select>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
          <label htmlFor="count" style={{ fontSize: "0.875rem", fontWeight: 500 }}>
            Bars
          </label>
          <input
            id="count"
            type="number"
            min="50"
            max="1000"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
            style={{ padding: "0.375rem 0.75rem", border: "1px solid #E0E0E0", borderRadius: "4px", fontSize: "0.875rem", width: "80px" }}
          />
        </div>
        <StatusBadge status={state} />
      </div>

      <section aria-labelledby="chart-heading" style={{ marginBottom: "1.5rem" }}>
        <h2 id="chart-heading" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          Price — {instrument.toUpperCase()} ({timeframe})
        </h2>
        <div role="img" aria-label="Price chart; data in the table below" style={{ height: 400 }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={candles} margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#E0E0E0" />
              <XAxis dataKey="t" tick={{ fontSize: 11 }} tickFormatter={(v) => new Date(v).toLocaleTimeString()} />
              <YAxis />
              <Tooltip formatter={tooltipFormatter} labelFormatter={tooltipLabelFormatter} />
              <Line type="monotone" dataKey="c" stroke="#1976D2" strokeWidth={1.5} name="Close" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.75rem" }}>
          <caption style={{ textAlign: "left", marginBottom: "0.5rem", fontWeight: 500 }}>
            Price data table (accessible alternative to the chart)
          </caption>
          <thead>
            <tr style={{ background: "#F5F5F5" }}>
              <th style={{ padding: "0.5rem", textAlign: "left", borderBottom: "1px solid #E0E0E0" }}>Time</th>
              <th style={{ padding: "0.5rem", textAlign: "right", borderBottom: "1px solid #E0E0E0" }}>Open</th>
              <th style={{ padding: "0.5rem", textAlign: "right", borderBottom: "1px solid #E0E0E0" }}>High</th>
              <th style={{ padding: "0.5rem", textAlign: "right", borderBottom: "1px solid #E0E0E0" }}>Low</th>
              <th style={{ padding: "0.5rem", textAlign: "right", borderBottom: "1px solid #E0E0E0" }}>Close</th>
            </tr>
          </thead>
          <tbody>
            {candles.slice(-50).map((c) => (
              <tr key={c.t} style={{ borderBottom: "1px solid #F0F0F0" }}>
                <td style={{ padding: "0.5rem", fontFamily: "monospace", fontSize: "0.75rem" }}>
                  {new Date(c.t).toLocaleString()}
                </td>
                <td style={{ padding: "0.5rem", textAlign: "right" }}>{c.o.toFixed(2)}</td>
                <td style={{ padding: "0.5rem", textAlign: "right" }}>{c.h.toFixed(2)}</td>
                <td style={{ padding: "0.5rem", textAlign: "right" }}>{c.l.toFixed(2)}</td>
                <td style={{ padding: "0.5rem", textAlign: "right" }}>{c.c.toFixed(2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </section>
  );
}