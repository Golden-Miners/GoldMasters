import { fetchProviders } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function DataProvidersPage() {
  const result = await fetchProviders();

  if (!result.available) {
    return <ExplicitState state="offline" />;
  }

  const providersData = result.data as {
    provider_id: string;
    status: string;
    market_open: boolean;
    terminal_build: string;
    last_bar_close_time: string | null;
    last_quote_time: string | null;
    checked_at: string;
  };

  return (
    <section className="panel" aria-labelledby="providers-heading">
      <header className="page-header">
        <h1 id="providers-heading" className="page-title">Data Providers</h1>
        <p className="page-subtitle">
          Provider health (terminal-closed/disconnected/missing-history/unsupported/healthy).
          Outage shows no market data.
        </p>
      </header>

      <div className="provider-card">
        <div className="provider-row">
          <span className="provider-label">Provider ID</span>
          <span className="provider-value num">{providersData.provider_id}</span>
        </div>
        <div className="provider-row">
          <span className="provider-label">Status</span>
          <span className="provider-value">
            <StatusBadge status={providersData.status} />
          </span>
        </div>
        <div className="provider-row">
          <span className="provider-label">Market Open</span>
          <span className="provider-value">{providersData.market_open ? "yes" : "no"}</span>
        </div>
        <div className="provider-row">
          <span className="provider-label">Terminal Build</span>
          <span className="provider-value num">{providersData.terminal_build}</span>
        </div>
        <div className="provider-row">
          <span className="provider-label">Last Bar Close</span>
          <span className="provider-value">
            {providersData.last_bar_close_time ? new Date(providersData.last_bar_close_time).toLocaleString() : "—"}
          </span>
        </div>
        <div className="provider-row">
          <span className="provider-label">Last Quote</span>
          <span className="provider-value">{providersData.last_quote_time ? new Date(providersData.last_quote_time).toLocaleString() : "—"}</span>
        </div>
        <div className="provider-row">
          <span className="provider-label">Checked At</span>
          <span className="provider-value">{new Date(providersData.checked_at).toLocaleString()}</span>
        </div>
      </div>
    </section>
  );
}
