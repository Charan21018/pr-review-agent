'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { motion } from 'framer-motion';
import { Bot, FileSearch, Gavel, LineChart } from 'lucide-react';

const LINKS = [
  { href: '/', label: 'Reviews', icon: FileSearch },
  { href: '/hitl', label: 'HITL Queue', icon: Gavel },
  { href: '/economics', label: 'Economics', icon: LineChart },
];

export function NavBar() {
  const pathname = usePathname();

  return (
    <header className="navbar">
      <div className="logo-container">
        <motion.div
          className="logo-icon-wrap"
          initial={{ rotate: -8, scale: 0.8, opacity: 0 }}
          animate={{ rotate: 0, scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 260, damping: 18 }}
        >
          <Bot size={18} strokeWidth={2.25} />
        </motion.div>
        <Link href="/" className="logo-text">AI PR Reviewer</Link>
      </div>

      <nav className="nav-links">
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active = pathname === href;
          return (
            <Link key={href} href={href} className={`nav-link${active ? ' active' : ''}`}>
              {active && (
                <motion.span
                  layoutId="nav-active-pill"
                  className="nav-active-pill"
                  transition={{ type: 'spring', stiffness: 380, damping: 32 }}
                  style={{
                    position: 'absolute',
                    inset: 0,
                    borderRadius: 999,
                    background: 'linear-gradient(135deg, var(--primary) 0%, #9333ea 100%)',
                    boxShadow: '0 4px 14px -4px rgba(124,107,247,0.55)',
                    zIndex: -1,
                  }}
                />
              )}
              <Icon size={15} strokeWidth={2.25} />
              <span className="nav-label">{label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="status-pulse">
        <span className="status-dot" />
        Live
      </div>
    </header>
  );
}
