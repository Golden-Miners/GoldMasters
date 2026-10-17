import { fetchProviders, fetchMarketBars } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function DataProvidersPage() {
  const [providersResult, quoteResult] = await Promise.all([
    fetchProviders(),
    fetchMarketBars("xauusd", "H1", 1),
  ]);

  if (!providersResult.available) {
    return <ExplicitState state="offline" />;
  }

  const providersData = providersResult.data as {
    provider_id: string;
    status: string;
    market_open: boolean;
    terminal_build: string;
    last_bar_close_time: string | null;
    last_quote_time: string | null;
    checked_at: string;
  };

  return (
    <section aria-labelledby="providers-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="providers-heading">Data Providers</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Provider health (5 states: terminal-closed/disconnected/missing-history/unsupported-symbol/healthy).
          Outage shows no market data.
        </p>
      </header>

      <div style={{ display: "flex", gap: "1rem", flexWrap: "wrap", marginBottom: "1.5rem" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "0.25rem", padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px", minWidth: "200px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Provider ID</span>
            <span style={{ fontWeight: 500, fontFamily: "monospace" }}>{providersData.provider_id}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Status</span>
            <StatusBadge status={providersData.status} />
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Market Open</span>
            <span style={{ fontWeight: 500 }}>{providersData.market_open ? "yes" : "no"}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Terminal Build</span>
            <span style={{ fontWeight: 500, fontFamily: "monospace" }}>{providersData.terminal_build}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Last Bar Close</span>
            <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
              {providersData.last_bar_close_time ? new Date(providersData.last_bar_close_time).toLocaleString() : "—"}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Last Quote</span>
            <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
              {providersData.last_quote_time ? new Date(providersData.last_quote_time).toLocaleString() : "—"}
            </span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <span style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Checked At</span>
            <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
              {new Date(providersData.checked_at).toLocaleString()}
            </span>
          </div>
        </div>
      </div>

      <section aria-labelledby="live-quote" style={{ marginTop: "2rem" }}>
        <h2 id="live-quote" style={{ fontSize: "1.125rem", marginBottom: "0.75rem" }}>
          Live Quote (XAUUSD H1)
        </h2>
        {quoteResult.available && quoteResult.bars.length > 0 ? (
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(150px, 1fr))", gap: "1rem" }}>
            <div style={{ padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px", textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Bid</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 600, fontFamily: "monospace" }}>
                {Number(quoteResult.bars[0].close).toFixed(2)}
              </div>
            </div>
            <div style={{ padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px", textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Ask</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 600, fontFamily: "monospace" }}>
                {Number(quoteResult.bars[0].close).toFixed(2)}
              </div>
            </div>
            <div style={{ padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px", textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Spread</div>
              <div style={{ fontSize: "1.5rem", fontWeight: 600, fontFamily: "monospace", color: "#1976D2" }}>
                0.00
              </div>
            </div>
            <div style={{ padding: "1rem", background: "#FAFAFA", border: "1px solid #E0E0E0", borderRadius: "8px", textAlign: "center" }}>
              <div style={{ fontSize: "0.75rem", color: "#757575", textTransform: "uppercase" }}>Timestamp</div>
              <div style={{ fontSize: "0.875rem", fontFamily: "monospace" }}>
                {new Date(quoteResult.bars[0].bar_close_time!).toLocaleString()}
              </div>
            </div>
          </div>
        ) : (
          <ExplicitState state="unavailable" />
        )}
      </section>
    </section>
  );
}