import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI PR Review Agent Dashboard",
  description: "Monitor and manage specialists PR reviews, cost models, and HITL authorization flows",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <header className="navbar">
          <div className="logo-container">
            <span style={{ fontSize: '1.5rem' }}>🤖</span>
            <Link href="/" className="logo-text">AI PR Reviewer</Link>
          </div>
          <nav className="nav-links">
            <Link href="/" className="nav-link">Reviews</Link>
            <Link href="/hitl" className="nav-link">HITL Queue</Link>
            <Link href="/economics" className="nav-link">Economics</Link>
          </nav>
        </header>
        {children}
      </body>
    </html>
  );
}
