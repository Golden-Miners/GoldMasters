import type { Metadata } from "next";
import Link from "next/link";
import Navbar from "./Navbar";
import "@/styles/globals.css";

export const metadata: Metadata = {
  title: "GoldMasters Research Console",
  description: "Local research signals over validated contracts. Signals only.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="app-shell" suppressHydrationWarning>
        <header className="app-header">
          <Navbar />
        </header>
        <main className="app-main">{children}</main>
        <footer className="app-footer">
          GoldMasters Research Console — Signals only. No trade execution.
        </footer>
      </body>
    </html>
  );
}
