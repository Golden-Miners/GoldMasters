import { fetchJournal } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import Link from "next/link";
import type { JournalEntry } from "../../generated/journal";

export const dynamic = "force-dynamic";

export default async function JournalPage() {
  const result = await fetchJournal();

  if (!result.available) {
    return <ExplicitState state="offline" />;
  }

  const entries = result.entries;

  if (entries.length === 0) {
    return (
      <section aria-labelledby="journal-heading">
        <header style={{ marginBottom: "1.5rem" }}>
          <h1 id="journal-heading">Journal</h1>
          <p style={{ color: "#616161", marginTop: "0.25rem" }}>
            Immutable decision snapshots with appended outcomes. Corrections via supersedes.
          </p>
        </header>
        <ExplicitState state="empty" />
      </section>
    );
  }

  return (
    <section aria-labelledby="journal-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="journal-heading">Journal</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Immutable decision snapshots with appended outcomes. Corrections via supersedes — never mutation.
        </p>
      </header>

      <div style={{ display: "flex", flexDirection: "column", gap: "0.5rem" }}>
        {entries.map((entry: JournalEntry) => (
          <Link
            key={entry.journal_id}
            href={`/decision?id=${entry.decision_id}`}
            style={{
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              padding: "0.75rem 1rem",
              background: "#FAFAFA",
              border: "1px solid #E0E0E0",
              borderRadius: "6px",
              textDecoration: "none",
              color: "inherit",
              transition: "background 0.15s, border-color 0.15s",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}>
              <StatusBadge status={entry.snapshot.decision} />
              <span style={{ fontFamily: "monospace", fontSize: "0.875rem" }}>
                {entry.snapshot.instrument_id}
              </span>
              <span style={{ fontSize: "0.75rem", color: "#757575" }}>
                {entry.snapshot.timeframe}
              </span>
              <span style={{ fontSize: "0.75rem", color: "#757575" }}>
                {entry.snapshot.strategy_id}@{entry.snapshot.strategy_version}
              </span>
              <time dateTime={entry.recorded_at} style={{ fontSize: "0.75rem", color: "#757575", fontFamily: "monospace" }}>
                {new Date(entry.recorded_at).toLocaleString()}
              </time>
            </div>
            <span style={{ fontSize: "0.75rem", color: "#757575" }}>
              journal_id: {entry.journal_id.slice(0, 8)}…
            </span>
          </Link>
        ))}
      </div>
    </section>
  );
}