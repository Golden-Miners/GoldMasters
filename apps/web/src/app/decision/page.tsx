import { fetchDecisions } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";
import Link from "next/link";
import type { DecisionRecord } from "../../generated/decision";

export const dynamic = "force-dynamic";

export default async function DecisionPage() {
  const decisionsResult = await fetchDecisions();

  if (!decisionsResult.available) {
    return (
      <section className="panel" aria-labelledby="decision-heading">
        <header className="page-header">
          <h1 id="decision-heading" className="page-title">
            Decision Detail
          </h1>
          <p className="page-subtitle">
            Evidence-ledger view of a qualified research candidate. No trade execution.
          </p>
        </header>
        <ExplicitState state="offline" />
      </section>
    );
  }

  const decisions = decisionsResult.decisions;

  if (decisions.length === 0) {
    return (
      <section className="panel" aria-labelledby="decision-heading">
        <header className="page-header">
          <h1 id="decision-heading" className="page-title">
            Decision Detail
          </h1>
          <p className="page-subtitle">
            Evidence-ledger view of a qualified research candidate. No trade execution.
          </p>
        </header>
        <ExplicitState state="empty" />
      </section>
    );
  }

  return (
    <section aria-labelledby="decision-heading">
      <header className="page-header">
        <h1 id="decision-heading" className="page-title">
          Decision Detail
        </h1>
        <p className="page-subtitle">
          Evidence-ledger view of a qualified research candidate. No trade execution.
        </p>
      </header>

      <div className="decision-list">
        {decisions.map((decision: DecisionRecord) => (
          <Link
            key={decision.decision_id}
            href={`/decision?id=${decision.decision_id}`}
            className="decision-item"
          >
            <div className="decision-left">
              <StatusBadge status={decision.decision} />
              <span className="decision-id">{decision.instrument_id}</span>
              <span className="strategy-meta-text">{decision.timeframe}</span>
              <span className="strategy-meta-text">
                {decision.strategy_id}@{decision.strategy_version}
              </span>
              {decision.direction && <StatusBadge status={decision.direction} />}
              <time dateTime={decision.created_at} className="recent-time">
                {new Date(decision.created_at).toLocaleString()}
              </time>
            </div>
            <span className="decision-right">Open Evidence →</span>
          </Link>
        ))}
      </div>
    </section>
  );
}
