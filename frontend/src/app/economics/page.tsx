'use client';

import React from 'react';
import { api, EconomicsData } from '../../lib/api';
import { CostChart } from '../../components/CostChart';

export default function EconomicsPage() {
  const [data, setData] = React.useState<EconomicsData | null>(null);
  const [loading, setLoading] = React.useState(true);
  const [budgetCap, setBudgetCap] = React.useState(100);

  const mockEconomics: EconomicsData = {
    daily_cost_usd: 0.3347,
    total_reviews_count: 12,
    average_latency_ms: 18450,
    total_tokens_consumed: 38400,
    agent_costs: {
      'security': 0.1245,
      'quality': 0.0842,
      'tests': 0.0421,
      'docs': 0.0211,
      'aggregator': 0.0628
    }
  };

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
    return (
      <div className="main-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading economics reports...</div>
      </div>
    );
  }

  const budgetUsagePercent = Math.min(100, (data.daily_cost_usd / budgetCap) * 100);

  return (
    <main className="main-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📈 Economics & Latency Dashboard</h1>
          <p>Continuous budget monitoring, LLM token optimization, and specialist agent cost structures.</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '2rem', alignItems: 'flex-start' }}>
        {/* Cost Breakdown & Legend Chart */}
        <div>
          <CostChart data={data} />
        </div>

        {/* Budget Config & Optimization Stats */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="card">
            <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>🛡️ Budget Guard</h3>
            <div style={{ marginBottom: '1.5rem' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                <span>Daily Token Cost</span>
                <span>${data.daily_cost_usd.toFixed(4)} / ${budgetCap.toFixed(2)}</span>
              </div>
              <div style={{ height: '0.5rem', backgroundColor: 'var(--background)', borderRadius: '999px', overflow: 'hidden', border: '1px solid var(--panel-border)' }}>
                <div style={{
                  height: '100%',
                  width: `${budgetUsagePercent}%`,
                  backgroundColor: budgetUsagePercent > 90 ? 'var(--error)' : budgetUsagePercent > 70 ? 'var(--warning)' : 'var(--success)',
                  transition: 'width 0.4s ease-out'
                }} />
              </div>
            </div>

            <div>
              <label style={{ display: 'block', fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>Adjust Daily Budget Cap ($)</label>
              <input
                type="range"
                min="5"
                max="500"
                step="5"
                value={budgetCap}
                onChange={(e) => setBudgetCap(Number(e.target.value))}
                style={{ width: '100%', accentColor: 'var(--primary)' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: '0.25rem' }}>
                <span>$5</span>
                <span>$500</span>
              </div>
            </div>
          </div>

          <div className="card">
            <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem' }}>⚡ Resource Optimization</h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', fontSize: '0.9rem' }}>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.8rem' }}>TOTAL TOKENS CONSUMED</span>
                <strong>{data.total_tokens_consumed.toLocaleString()} tokens</strong>
              </div>
              <div>
                <span style={{ color: 'var(--text-muted)', display: 'block', fontSize: '0.8rem' }}>ESTIMATED COST PER REVIEW</span>
                <strong>${(data.daily_cost_usd / (data.total_reviews_count || 1)).toFixed(4)}</strong>
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
