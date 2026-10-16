import type { Metadata } from "next";
import Link from "next/link";

export const metadata: Metadata = {
  title: "GoldMasters Research Console",
  description: "Local research signals over validated contracts. Signals only.",
};

const NAV_LINKS = [
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
      <body>
        <nav aria-label="Console surfaces">
          <ul>
            {NAV_LINKS.map((link) => (
              <li key={link.href}>
                <Link href={link.href}>{link.label}</Link>
              </li>
            ))}
          </ul>
        </nav>
        {children}
      </body>
    </html>
  );
}
