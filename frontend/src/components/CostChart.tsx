'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  PieChart, Pie, Cell, ResponsiveContainer, Tooltip,
} from 'recharts';
import { EconomicsData } from '../lib/api';

interface CostChartProps {
  data: EconomicsData;
}

const AGENT_COLORS: Record<string, string> = {
  security: '#fb7185',
  quality: '#38bdf8',
  tests: '#fbbf24',
  docs: '#34d399',
  aggregator: '#a78bfa',
  orchestrator: '#a78bfa',
};

const FALLBACK_COLORS = ['#7c6bf7', '#f472b6', '#22d3ee', '#fbbf24', '#34d399'];

function colorFor(agent: string, idx: number) {
  return AGENT_COLORS[agent.toLowerCase()] || FALLBACK_COLORS[idx % FALLBACK_COLORS.length];
}

function CustomTooltip({ active, payload }: any) {
  if (!active || !payload || !payload.length) return null;
  const p = payload[0];
  return (
    <div
      style={{
        background: 'rgba(11,14,23,0.95)',
        border: '1px solid var(--panel-border)',
        borderRadius: 10,
        padding: '0.6rem 0.85rem',
        fontSize: '0.8rem',
        boxShadow: 'var(--shadow-lg)',
        backdropFilter: 'blur(8px)',
      }}
    >
      <div style={{ fontWeight: 700, textTransform: 'capitalize', marginBottom: 2 }}>{p.name}</div>
      <div style={{ color: 'var(--text-muted)' }}>${Number(p.value).toFixed(4)}</div>
    </div>
  );
}

export const CostChart: React.FC<CostChartProps> = ({ data }) => {
  const agentCosts = data.agent_costs || {};
  const hasRealData = Object.values(agentCosts).some((v) => v > 0);

  const costs = hasRealData ? agentCosts : {
    security: 0.125, quality: 0.084, tests: 0.042, docs: 0.021, aggregator: 0.063,
  };
  const displayTotal = Object.values(costs).reduce((s, v) => s + v, 0) || 1;

  const chartData = Object.entries(costs)
    .filter(([, v]) => v > 0)
    .map(([agent, cost]) => ({ name: agent, value: cost }));

  return (
    <motion.div
      className="card card-hover"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
    >
      <h3 style={{ fontSize: '1.05rem', marginBottom: '0.25rem' }}>Cost Breakdown by Agent</h3>
      <p style={{ fontSize: '0.8rem', marginBottom: '1rem' }}>
        {hasRealData ? 'Live spend distribution across the pipeline' : 'Sample data — no spend recorded yet'}
      </p>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(180px, 220px) 1fr', gap: '1.5rem', alignItems: 'center' }}>
        <div style={{ position: 'relative', height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                innerRadius={58}
                outerRadius={82}
                paddingAngle={3}
                startAngle={90}
                endAngle={-270}
                animationDuration={900}
                animationEasing="ease-out"
                stroke="none"
              >
                {chartData.map((entry, idx) => (
                  <Cell key={entry.name} fill={colorFor(entry.name, idx)} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
          <div
            style={{
              position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column',
              alignItems: 'center', justifyContent: 'center', pointerEvents: 'none',
            }}
          >
            <span style={{ fontSize: '1.3rem', fontWeight: 800 }}>${displayTotal.toFixed(3)}</span>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>total</span>
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
          {Object.entries(costs).map(([agent, cost], idx) => {
            const pct = (cost / displayTotal) * 100;
            return (
              <motion.div
                key={agent}
                initial={{ opacity: 0, x: 12 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.15 + idx * 0.06, duration: 0.4 }}
                style={{ display: 'flex', alignItems: 'center', gap: '0.7rem' }}
              >
                <span style={{ display: 'block', width: '0.6rem', height: '0.6rem', borderRadius: '50%', background: colorFor(agent, idx), flexShrink: 0 }} />
                <span style={{ fontSize: '0.85rem', textTransform: 'capitalize', flex: 1 }}>{agent}</span>
                <div style={{ flex: 1, height: 6, background: 'rgba(255,255,255,0.05)', borderRadius: 999, overflow: 'hidden', maxWidth: 90 }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${pct}%` }}
                    transition={{ delay: 0.2 + idx * 0.06, duration: 0.7, ease: [0.16, 1, 0.3, 1] }}
                    style={{ height: '100%', background: colorFor(agent, idx), borderRadius: 999 }}
                  />
                </div>
                <span style={{ fontSize: '0.82rem', fontWeight: 700, minWidth: 62, textAlign: 'right' }}>${cost.toFixed(4)}</span>
              </motion.div>
            );
          })}
        </div>
      </div>
    </motion.div>
  );
};
