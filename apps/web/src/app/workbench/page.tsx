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
  c: string;
}

export default function WorkbenchPage() {
  const [state, setState] = useState<
    "loading" | "empty" | "ready" | "offline" | "unavailable"
  >("loading");
  const [candles, setCandles] = useState<CandlePoint[]>([]);
  const [instrument, setInstrument] = useState("xauusd");
  const [timeframe, setTimeframe] = useState("H1");
  const [count, setCount] = useState(200);

  const fetchData = async () => {
    setState("loading");
    try {
      const result = await fetchMarketBars(instrument, timeframe, count);
      if (!result.available) {
        setCandles([]);
        setState("unavailable");
        return;
      }
      if (result.bars.length === 0) {
        setCandles([]);
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
      setCandles([]);
      setState("unavailable");
    }
  };

  useEffect(() => {
    fetchData();
  }, [instrument, timeframe, count]);

  return (
    <section aria-labelledby="workbench-heading">
      <header className="page-header">
        <h1 id="workbench-heading" className="page-title">
          Instrument Workbench
        </h1>
        <p className="page-subtitle">
          Closed-bar analysis with chart and tabular data alternative.
        </p>
      </header>

      <div className="controls-bar">
        <div className="control-group">
          <label htmlFor="instrument" className="control-label">
            Instrument
          </label>
          <select
            id="instrument"
            className="control-select"
            value={instrument}
            onChange={(e) => setInstrument(e.target.value)}
          >
            <option value="xauusd">XAUUSD (Gold)</option>
            <option value="xagusd">XAGUSD (Silver)</option>
            <option value="eurusd">EURUSD</option>
            <option value="gbpusd">GBPUSD</option>
            <option value="btcusd">BTCUSD</option>
            <option value="ethusd">ETHUSD</option>
          </select>
        </div>
        <div className="control-group">
          <label htmlFor="timeframe" className="control-label">
            Timeframe
          </label>
          <select
            id="timeframe"
            className="control-select"
            value={timeframe}
            onChange={(e) => setTimeframe(e.target.value)}
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
        <div className="control-group">
          <label htmlFor="count" className="control-label">
            Bars
          </label>
          <input
            id="count"
            className="control-input"
            type="number"
            min="50"
            max="1000"
            value={count}
            onChange={(e) => setCount(Number(e.target.value))}
          />
        </div>
        <span className="gm-badge gm-badge-neutral">{state}</span>
      </div>

      {state === "loading" ? (
        <ExplicitState state="loading" />
      ) : state === "unavailable" ? (
        <ExplicitState state="unavailable">
          <p>
            Market data unavailable. Please check your MT5 connection and try again.
          </p>
        </ExplicitState>
      ) : state === "empty" ? (
        <ExplicitState state="empty" />
      ) : (
        <section className="panel" aria-labelledby="chart-heading">
          <h2 id="chart-heading" className="section-heading">
            Close Price — {instrument.toUpperCase()} ({timeframe})
          </h2>
          <div className="chart-wrap" role="img" aria-label="Price chart; data in the table below">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={candles} margin={{ top: 10, right: 30, left: 20, bottom: 10 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--gm-border)" />
                <XAxis
                  dataKey="t"
                  tick={{ fontSize: 11 }}
                  tickFormatter={(v: string) => new Date(v).toLocaleTimeString()}
                />
                <YAxis />
                <Tooltip
                  formatter={(value: any, name: string | number | undefined) =>
                    typeof value === "number" ? value.toFixed(2) : "-"
                  }
                  labelFormatter={(v: React.ReactNode) =>
                    typeof v === "string" ? new Date(v).toLocaleString() : String(v)
                  }
                />
                <Line type="monotone" dataKey="c" stroke="var(--gm-accent)" strokeWidth={1.5} name="Close" />
              </LineChart>
            </ResponsiveContainer>
          </div>

          <table className="chart-table">
            <caption>Price data table (accessible alternative to the chart)</caption>
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
              {candles.slice(-50).map((c) => (
                <tr key={c.t}>
                  <td className="num">
                    {new Date(c.t).toLocaleString()}
                  </td>
                  <td className="num-col">{c.o.toFixed(2)}</td>
                  <td className="num-col">{c.h.toFixed(2)}</td>
                  <td className="num-col">{c.l.toFixed(2)}</td>
                  <td className="num-col">{c.c}</td>
                  <td className="num-col">—</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      )}
    </section>
  );
}