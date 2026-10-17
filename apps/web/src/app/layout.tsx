import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "GoldMasters Research Console",
  description: "Local research signals over validated contracts. Signals only.",
};

const nav = [
  { href: "/overview", label: "Overview" },
  { href: "/workbench", label: "Instrument Workbench" },
  { href: "/decision", label: "Decision Detail" },
  { href: "/news-sentiment", label: "News & Sentiment" },
  { href: "/strategy-lab", label: "Strategy Lab" },
  { href: "/backtest", label: "Backtest Results" },
  { href: "/journal", label: "Journal" },
  { href: "/agent-runs", label: "Agent Runs" },
  { href: "/data-providers", label: "Data Providers" },
  { href: "/settings", label: "Settings/Model Health" },
  { href: "/system-health", label: "System Health" },
];

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: 0, minHeight: "100vh", display: "flex", flexDirection: "column" }}>
        <header
          style={{
            borderBottom: "1px solid #E0E0E0",
            padding: "0.75rem 1.5rem",
            background: "#FAFAFA",
            position: "sticky",
            top: 0,
            zIndex: 10,
          }}
        >
          <nav style={{ display: "flex", gap: "1rem", flexWrap: "wrap", maxWidth: "1200px", margin: "0 auto" }}>
            <Link href="/" style={{ fontWeight: 600, textDecoration: "none", color: "#1A1A1A" }}>
              GoldMasters
            </Link>
            <div style={{ display: "flex", gap: "0.5rem", flexWrap: "wrap", flex: 1 }}>
              {nav.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  style={{
                    padding: "0.375rem 0.75rem",
                    borderRadius: "4px",
                    textDecoration: "none",
                    color: "#37474F",
                    fontSize: "0.875rem",
                    fontWeight: 500,
                    border: "1px solid transparent",
                    transition: "background 0.15s, border-color 0.15s",
                  }}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </nav>
        </header>
        <main style={{ flex: 1, padding: "1.5rem", maxWidth: "1200px", margin: "0 auto", width: "100%" }}>
          {children}
        </main>
        <footer
          style={{
            borderTop: "1px solid #E0E0E0",
            padding: "1rem 1.5rem",
            background: "#FAFAFA",
            fontSize: "0.75rem",
            color: "#757575",
            textAlign: "center",
          }}
        >
          GoldMasters Research Console — Signals only. No trade execution.
        </footer>
      </body>
    </html>
  );
}