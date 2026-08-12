'use client';

import React from 'react';
import { motion } from 'framer-motion';
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import {
  Zap, ShieldCheck, Sparkles, FlaskConical, FileText, Handshake, Settings2, Radar,
} from 'lucide-react';
import { TraceEvent } from '../lib/api';

interface AgentTimelineProps {
  events: TraceEvent[];
}

const AGENT_ICON: Record<string, React.ElementType> = {
  security: ShieldCheck,
  quality: Sparkles,
  tests: FlaskConical,
  docs: FileText,
  aggregator: Handshake,
  orchestrator: Handshake,
  retriever: Radar,
};

const AGENT_COLOR: Record<string, string> = {
  security: '#fb7185',
  quality: '#38bdf8',
  tests: '#fbbf24',
  docs: '#34d399',
  aggregator: '#a78bfa',
  orchestrator: '#a78bfa',
  retriever: '#22d3ee',
};

function iconFor(type: string, agent: string) {
  if (type.includes('start')) return Zap;
  return AGENT_ICON[agent.toLowerCase()] || Settings2;
}

function colorFor(agent: string) {
  return AGENT_COLOR[agent.toLowerCase()] || '#7c6bf7';
}

function formatLatency(ms?: number) {
  if (ms === undefined) return '';
  return ms > 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`;
}

function LatencyTooltip({ active, payload, label }: any) {
  if (!active || !payload || !payload.length) return null;
  return (
    <div style={{
      background: 'rgba(11,14,23,0.95)', border: '1px solid var(--panel-border)',
      borderRadius: 10, padding: '0.5rem 0.75rem', fontSize: '0.78rem', backdropFilter: 'blur(8px)',
    }}
    >
      <div style={{ fontWeight: 700, textTransform: 'capitalize' }}>{label}</div>
      <div style={{ color: 'var(--text-muted)' }}>{formatLatency(payload[0].value)}</div>
    </div>
  );
}

export const AgentTimeline: React.FC<AgentTimelineProps> = ({ events }) => {
  const sortedEvents = [...events].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());

  const latencyData = sortedEvents
    .filter((e) => e.latency_ms !== undefined && e.latency_ms > 0)
    .map((e) => ({ name: e.agent, latency: e.latency_ms as number }));

  return (
    <div style={{ padding: '0.5rem 0' }}>
      {latencyData.length > 0 && (
        <motion.div
          className="card"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          style={{ marginBottom: '2rem' }}
        >
          <h3 style={{ fontSize: '0.95rem', marginBottom: '1rem' }}>Latency by Step</h3>
          <div style={{ height: 160 }}>
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={latencyData} margin={{ top: 4, right: 8, bottom: 0, left: -20 }}>
                <XAxis dataKey="name" tick={{ fill: 'var(--text-muted)', fontSize: 11, textTransform: 'capitalize' }} axisLine={{ stroke: 'var(--panel-border)' }} tickLine={false} />
                <YAxis tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <Tooltip content={<LatencyTooltip />} cursor={{ fill: 'rgba(255,255,255,0.03)' }} />
                <Bar dataKey="latency" radius={[6, 6, 0, 0]} animationDuration={800}>
                  {latencyData.map((d, i) => (
                    <Cell key={i} fill={colorFor(d.name)} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </motion.div>
      )}

      <h3 style={{ fontSize: '1.05rem', marginBottom: '1.25rem' }}>Execution Trace Timeline</h3>

      {sortedEvents.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
          No trace events logged for this review task.
        </div>
      ) : (
        <div style={{ position: 'relative', marginLeft: '1rem', paddingLeft: '1.75rem' }}>
          <motion.div
            initial={{ scaleY: 0 }}
            animate={{ scaleY: 1 }}
            transition={{ duration: Math.min(sortedEvents.length * 0.15, 1.4), ease: 'easeOut' }}
            style={{
              position: 'absolute', left: 0, top: 0, bottom: 0, width: 2,
              background: 'linear-gradient(to bottom, var(--primary), transparent)',
              transformOrigin: 'top',
            }}
          />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
            {sortedEvents.map((evt, idx) => {
              const Icon = iconFor(evt.event_type, evt.agent);
              const color = colorFor(evt.agent);
              return (
                <motion.div
                  key={evt.id}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.09, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                  style={{ position: 'relative' }}
                >
                  <motion.span
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ delay: idx * 0.09 + 0.1, type: 'spring', stiffness: 400, damping: 18 }}
                    style={{
                      position: 'absolute', left: '-2.35rem', top: 0,
                      background: 'var(--background-alt)', border: `2px solid ${color}`,
                      borderRadius: '50%', width: '1.6rem', height: '1.6rem',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color, boxShadow: `0 0 12px ${color}55`,
                    }}
                  >
                    <Icon size={12} strokeWidth={2.5} />
                  </motion.span>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.3rem', gap: '0.5rem', flexWrap: 'wrap' }}>
                    <span style={{ fontWeight: 700, fontSize: '0.88rem', textTransform: 'capitalize' }}>
                      {evt.agent} &middot; <span style={{ fontWeight: 500, color: 'var(--text-muted)' }}>{evt.event_type}</span>
                    </span>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>
                      {new Date(evt.ts).toLocaleTimeString()}
                    </span>
                  </div>

                  <div className="card" style={{ padding: '0.85rem 1rem', fontSize: '0.82rem' }}>
                    {evt.model && <div style={{ marginBottom: '0.3rem' }}>Model: <code style={{ color: 'var(--primary-2)' }}>{evt.model}</code></div>}

                    {evt.latency_ms !== undefined && evt.latency_ms > 0 && (
                      <div style={{ marginBottom: '0.3rem' }}>
                        Latency: <strong>{formatLatency(evt.latency_ms)}</strong>
                      </div>
                    )}

                    {evt.tokens_in !== undefined && (
                      <div style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>
                        Tokens: {evt.tokens_in} in / {evt.tokens_out} out &middot; Cost: ${evt.cost_usd?.toFixed(4)}
                      </div>
                    )}

                    {evt.outcome && (
                      <div style={{ marginTop: '0.3rem' }}>
                        Status: <span style={{ color: evt.outcome === 'success' ? 'var(--success)' : 'var(--error)' }}>{evt.outcome}</span>
                        {evt.confidence !== undefined && ` · Confidence: ${(evt.confidence * 100).toFixed(0)}%`}
                      </div>
                    )}

                    {evt.payload && Object.keys(evt.payload).length > 0 && (
                      <div style={{ marginTop: '0.5rem', borderTop: '1px dashed var(--panel-border)', paddingTop: '0.5rem' }}>
                        <details>
                          <summary style={{ cursor: 'pointer', color: 'var(--primary-2)', outline: 'none' }}>View Payload</summary>
                          <pre style={{
                            marginTop: '0.4rem', padding: '0.6rem', background: '#050710', color: 'var(--text-muted)',
                            fontSize: '0.74rem', borderRadius: '6px', overflowX: 'auto', fontFamily: 'var(--font-mono)',
                          }}
                          >
                            {JSON.stringify(evt.payload, null, 2)}
                          </pre>
                        </details>
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};
