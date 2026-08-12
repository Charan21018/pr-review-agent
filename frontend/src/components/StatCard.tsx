'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface StatCardProps {
  icon: React.ReactNode;
  label: string;
  value: number;
  format?: (v: number) => string;
  accent?: string;
  delay?: number;
}

// requestAnimationFrame-driven count-up — deliberately dependency-free so it
// isn't at the mercy of whichever animate() overload this framer-motion
// version resolves for a bare number (this repo pins a version with several
// breaking API changes from older docs/training data).
function easeOutExpo(t: number): number {
  return t === 1 ? 1 : 1 - 2 ** (-10 * t);
}

export const StatCard: React.FC<StatCardProps> = ({
  icon,
  label,
  value,
  format,
  accent = 'var(--primary-2)',
  delay = 0,
}) => {
  const [display, setDisplay] = React.useState(() => (format ? format(0) : '0'));

  React.useEffect(() => {
    let raf = 0;
    let start = 0;
    const durationMs = 1000;
    const delayMs = delay * 1000;
    const finalDisplay = format ? format(value) : Math.round(value).toLocaleString();

    const tick = (ts: number) => {
      if (!start) start = ts;
      const elapsed = ts - start - delayMs;
      if (elapsed < 0) {
        raf = requestAnimationFrame(tick);
        return;
      }
      const progress = Math.min(1, elapsed / durationMs);
      const current = value * easeOutExpo(progress);
      setDisplay(format ? format(current) : Math.round(current).toLocaleString());
      if (progress < 1) raf = requestAnimationFrame(tick);
    };

    raf = requestAnimationFrame(tick);

    // Safety net: browsers pause/throttle requestAnimationFrame for hidden or
    // backgrounded tabs, which would otherwise leave the counter stuck at 0
    // indefinitely. setTimeout still fires (even if throttled) regardless of
    // tab visibility, so this guarantees the correct final value lands.
    const fallback = setTimeout(() => setDisplay(finalDisplay), delayMs + durationMs + 150);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(fallback);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <motion.div
      className="card card-hover stat-card"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <div className="stat-card-icon" style={{ color: accent }}>{icon}</div>
      <div className="stat-card-value">{display}</div>
      <div className="stat-card-label">{label}</div>
    </motion.div>
  );
};
