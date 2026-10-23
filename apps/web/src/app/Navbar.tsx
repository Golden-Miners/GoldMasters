"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState, useEffect } from "react";

const navGroups = [
  {
    label: "Market Data",
    items: [
      { href: "/overview", label: "Overview" },
      { href: "/workbench", label: "Instrument Workbench" },
      { href: "/data-providers", label: "Data Providers" },
    ],
  },
  {
    label: "Analysis",
    items: [
      { href: "/decision", label: "Decision Detail" },
      { href: "/news-sentiment", label: "News & Sentiment" },
      { href: "/strategy-lab", label: "Strategy Lab" },
    ],
  },
  {
    label: "Results",
    items: [
      { href: "/backtest", label: "Backtest Results" },
      { href: "/journal", label: "Journal" },
      { href: "/agent-runs", label: "Agent Runs" },
    ],
  },
  {
    label: "System",
    items: [
      { href: "/settings", label: "Settings/Model Health" },
      { href: "/system-health", label: "System Health" },
    ],
  },
];

export default function Navbar() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (label: string) => {
    setOpenGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  const isGroupOpen = (label: string) => openGroups.has(label);

  const closeAll = () => {
    setOpenGroups(new Set());
    setMobileOpen(false);
  };

  // Close all menus on Escape
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeAll();
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, []);

  // Close all menus when clicking outside the nav
  useEffect(() => {
    const handleClick = (event: MouseEvent) => {
      const container = document.getElementById("nav-container");
      if (!container?.contains(event.target as Node)) {
        setOpenGroups(new Set());
        setMobileOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <nav className="app-nav" id="nav-container">
      <Link href="/" className="app-brand">
        GoldMasters
      </Link>

      {/* Desktop dropdown navigation */}
      <div className="nav-desktop">
        {navGroups.map((group) => (
          <div key={group.label} className="nav-dropdown">
            <button
              className={`nav-dropdown-trigger ${isGroupOpen(group.label) ? "open" : ""}`}
              onClick={() => toggleGroup(group.label)}
              aria-expanded={isGroupOpen(group.label)}
              aria-haspopup="true"
            >
              {group.label}
              <span className="nav-dropdown-arrow">▾</span>
            </button>
            <div className="nav-dropdown-menu">
              {group.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`nav-dropdown-link ${pathname === item.href ? "active" : ""}`}
                  onClick={() => setOpenGroups(new Set())}
                >
                  {item.label}
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Mobile toggle */}
      <div className="nav-mobile">
        <button
          className="nav-mobile-toggle"
          onClick={() => setMobileOpen(!mobileOpen)}
          aria-expanded={mobileOpen}
          aria-label="Open navigation menu"
        >
          <span className="nav-hamburger-line" />
          <span className="nav-hamburger-line" />
          <span className="nav-hamburger-line" />
        </button>
        {mobileOpen && (
          <div className="nav-mobile-menu">
            {navGroups.map((group) => (
              <div key={group.label} className="nav-mobile-group">
                <button
                  className={`nav-mobile-group-toggle ${isGroupOpen(group.label) ? "open" : ""}`}
                  onClick={() => toggleGroup(group.label)}
                >
                  {group.label}
                  <span className="nav-group-arrow">{isGroupOpen(group.label) ? "▾" : "▸"}</span>
                </button>
                <div className={`nav-mobile-group-links ${isGroupOpen(group.label) ? "open" : ""}`}>
                  {group.items.map((item) => (
                    <Link
                      key={item.href}
                      href={item.href}
                      className={`nav-mobile-link ${pathname === item.href ? "active" : ""}`}
                      onClick={() => setMobileOpen(false)}
                    >
                      {item.label}
                    </Link>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
