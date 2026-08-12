'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  LineChart as LineChartIcon, DollarSign, FileSearch, Timer, Cpu, ShieldHalf, Zap,
} from 'lucide-react';
import { api, EconomicsData } from '../../lib/api';
import { CostChart } from '../../components/CostChart';
import { StatCard } from '../../components/StatCard';
import { PageSkeleton } from '../../components/Skeleton';

const mockEconomics: EconomicsData = {
  daily_cost_usd: 0.3347,
  total_reviews_count: 12,
  average_latency_ms: 18450,
  total_tokens_consumed: 38400,
  agent_costs: {
    security: 0.1245, quality: 0.0842, tests: 0.0421, docs: 0.0211, aggregator: 0.0628,
  },
};

export default function EconomicsPage() {
  const [data, setData] = React.useState<EconomicsData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [budgetCap, setBudgetCap] = React.useState(100);

  React.useEffect(() => {
    async function loadEconomics() {
      try {
        const econ = await api.getEconomics();
        setData(econ);
      } catch (err) {
        console.warn('API connection failed. Loading local mock economics data.', err);
        setData(mockEconomics);
      } finally {
        setLoading(false);
      }
    }
    loadEconomics();
  }, []);

  if (loading || !data) {
    return <PageSkeleton label="Loading economics reports…" />;
  }

  const budgetUsagePercent = Math.min(100, (data.daily_cost_usd / budgetCap) * 100);
  const budgetColor = budgetUsagePercent > 90 ? 'var(--error)' : budgetUsagePercent > 70 ? 'var(--warning)' : 'var(--success)';

  return (
    <main className="main-container">
      <motion.div
        className="page-header"
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45 }}
      >
        <div>
          <h1 className="page-title">
            <span className="page-title-icon"><LineChartIcon size={20} /></span>
            <span className="text-gradient">Economics &amp; Latency</span>
          </h1>
          <p>Continuous budget monitoring, LLM token optimization, and specialist agent cost structures.</p>
        </div>
      </motion.div>

      <div className="stats-grid">
        <StatCard icon={<DollarSign size={18} />} label="Daily Cost" value={data.daily_cost_usd} format={(v) => `$${v.toFixed(4)}`} accent="var(--accent-amber)" delay={0} />
        <StatCard icon={<FileSearch size={18} />} label="Reviews Executed" value={data.total_reviews_count} accent="var(--success)" delay={0.05} />
        <StatCard icon={<Timer size={18} />} label="Avg Latency" value={data.average_latency_ms} format={(v) => (v > 1000 ? `${(v / 1000).toFixed(1)}s` : `${Math.round(v)}ms`)} accent="var(--info)" delay={0.1} />
        <StatCard icon={<Cpu size={18} />} label="Total Tokens" value={data.total_tokens_consumed} accent="var(--primary-2)" delay={0.15} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem', alignItems: 'flex-start' }}>
        <CostChart data={data} />

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <motion.div
            className="card"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.1, duration: 0.5 }}
          >
            <h3 style={{ fontSize: '1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldHalf size={16} color="var(--primary-2)" /> Budget Guard
            </h3>
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                <span>Daily Token Cost</span>
                <span>${data.daily_cost_usd.toFixed(4)} / ${budgetCap.toFixed(2)}</span>
              </div>
              <div style={{ height: '0.6rem', backgroundColor: 'var(--background)', borderRadius: '999px', overflow: 'hidden', border: '1px solid var(--panel-border)' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${budgetUsagePercent}%` }}
                  transition={{ duration: 0.9, ease: [0.16, 1, 0.3, 1], delay: 0.3 }}
                  style={{ height: '100%', background: `linear-gradient(90deg, ${budgetColor}, ${budgetColor})`, boxShadow: `0 0 10px ${budgetColor}88` }}
                />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.82rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Adjust Daily Budget Cap ($)</label>
              <input
                type="range"
                min="5"
                max="500"
                step="5"
                value={budgetCap}
                onChange={(e) => setBudgetCap(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                <span>$5</span>
                <span>$500</span>
              </div>
            </div>
          </motion.div>

          <motion.div
            className="card"
            initial={{ opacity: 0, x: 16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.2, duration: 0.5 }}
          >
            <h3 style={{ fontSize: '1rem', marginBottom: '1rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={16} color="var(--accent-amber)" /> Resource Optimization
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.9rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Total Tokens Consumed</span>
                <strong>{data.total_tokens_consumed.toLocaleString()} tokens</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.75rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>Est. Cost Per Review</span>
                <strong>${(data.daily_cost_usd / (data.total_reviews_count || 1)).toFixed(4)}</strong>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </main>
  );
}
