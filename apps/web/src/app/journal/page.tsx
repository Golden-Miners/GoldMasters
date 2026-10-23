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
      <section className="panel" aria-labelledby="journal-heading">
        <header className="page-header">
          <h1 id="journal-heading" className="page-title">Journal</h1>
          <p className="page-subtitle">
            Immutable decision snapshots with appended outcomes. Corrections via supersedes — never mutation.
          </p>
        </header>
        <ExplicitState state="empty" />
      </section>
    );
  }

  return (
    <section className="panel" aria-labelledby="journal-heading">
      <header className="page-header">
        <h1 id="journal-heading" className="page-title">Journal</h1>
        <p className="page-subtitle">
          Immutable decision snapshots with appended outcomes. Corrections via supersedes — never mutation.
        </p>
      </header>

      <div className="journal-list">
        {entries.map((entry: JournalEntry) => (
          <Link
            key={entry.journal_id}
            href={`/decision?id=${entry.decision_id}`}
            className="journal-item"
          >
            <div className="journal-left">
              <StatusBadge status={entry.snapshot.decision} />
              <span className="num">{entry.snapshot.instrument_id}</span>
              <span className="text-muted">{entry.snapshot.timeframe}</span>
              <span className="text-muted">
                {entry.snapshot.strategy_id}@{entry.snapshot.strategy_version}
              </span>
              <time dateTime={entry.recorded_at} className="decision-time">
                {new Date(entry.recorded_at).toLocaleString()}
              </time>
            </div>
            <span className="journal-right">journal_id: {entry.journal_id.slice(0, 8)}…</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
