import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "GoldMasters Research Console",
  description: "Local research signals over validated contracts. Signals only.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
