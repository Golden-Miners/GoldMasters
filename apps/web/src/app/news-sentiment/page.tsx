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
      <section aria-labelledby="news-heading">
        <header style={{ marginBottom: "1.5rem" }}>
          <h1 id="news-heading">News & Sentiment</h1>
          <p style={{ color: "#616161", marginTop: "0.25rem" }}>
            Source-attributed news items and sentiment evidence.
          </p>
        </header>
        <StatusBadge status={data.status} />
        <p style={{ marginTop: "0.75rem", color: "#757575" }}>
          {data.limitations.join("; ")}
        </p>
      </section>
    );
  }

  return (
    <section aria-labelledby="news-heading">
      <header style={{ marginBottom: "1.5rem" }}>
        <h1 id="news-heading">News & Sentiment</h1>
        <p style={{ color: "#616161", marginTop: "0.25rem" }}>
          Source-attributed news items and sentiment evidence.
        </p>
      </header>
      <div style={{ marginBottom: "1rem" }}>
        <StatusBadge status={data.status} />
      </div>
      <ul style={{ listStyle: "none", padding: 0, display: "flex", flexDirection: "column", gap: "0.75rem" }}>
        {data.items.map((item: any, index: number) => (
          <li
            key={index}
            style={{
              padding: "1rem",
              background: "#FAFAFA",
              border: "1px solid #E0E0E0",
              borderRadius: "8px",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "0.5rem" }}>
              <span style={{ fontWeight: 500 }}>{item.source_id ?? "unknown"}</span>
              <time dateTime={item.published_at} style={{ fontSize: "0.75rem", color: "#757575" }}>
                {new Date(item.published_at).toLocaleString()}
              </time>
            </div>
            <h3 style={{ margin: "0 0 0.5rem", fontSize: "1rem" }}>{item.title}</h3>
            <p style={{ margin: 0, color: "#424242" }}>{item.content ?? item.summary ?? "No content"}</p>
            <div style={{ marginTop: "0.5rem", fontSize: "0.75rem", color: "#757575" }}>
              Retrieved: {item.retrieved_at ? new Date(item.retrieved_at).toLocaleString() : "unknown"} |
              Limitations: {item.limitations?.join(", ") ?? "none declared"}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}