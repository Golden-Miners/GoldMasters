import { fetchNewsSentiment } from "../../lib/api";
import { StatusBadge } from "../../components/StatusBadge";
import { ExplicitState } from "../../components/ExplicitState";

export const dynamic = "force-dynamic";

export default async function NewsSentimentPage() {
  const result = await fetchNewsSentiment();

  if (!result.available) {
    return <ExplicitState state="offline" />;
  }

  const { data } = result;

  if (data.items.length === 0) {
    return (
      <section className="panel" aria-labelledby="news-heading">
        <header className="page-header">
          <h1 id="news-heading" className="page-title">
            News & Sentiment
          </h1>
          <p className="page-subtitle">
            Source-attributed news items and sentiment evidence.
          </p>
        </header>
        <div className="empty-state" style={{ marginBottom: "var(--gm-space-3)" }}>
          <span className="gm-badge gm-badge-unavailable">Unavailable</span>
          <span className="text-muted">{data.limitations.join("; ")}</span>
        </div>
      </section>
    );
  }

  return (
    <section className="panel" aria-labelledby="news-heading">
      <header className="page-header">
        <h1 id="news-heading" className="page-title">
          News & Sentiment
        </h1>
        <p className="page-subtitle">
          Source-attributed news items and sentiment evidence.
        </p>
      </header>

      <div className="empty-state" style={{ marginBottom: "var(--gm-space-3)" }}>
        <StatusBadge status={data.status} />
      </div>

      <div className="news-list">
        {data.items.map((item: any, index: number) => (
          <div className="news-item" key={index}>
            <div className="news-head">
              <span className="news-source">{item.source_id ?? "unknown"}</span>
              <time dateTime={item.published_at} className="news-time">
                {new Date(item.published_at).toLocaleString()}
              </time>
            </div>
            <h3 className="news-title">{item.title}</h3>
            <p className="news-body">
              {item.content ?? item.summary ?? "No content"}
            </p>
            <div className="news-meta">
              <span>
                Retrieved:
                {item.retrieved_at
                  ? new Date(item.retrieved_at).toLocaleString()
                  : "unknown"}
              </span>
              <span>
                Limitations: {item.limitations?.join(", ") ?? "none declared"}
              </span>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}