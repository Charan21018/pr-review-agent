import React from 'react';
import { TraceEvent } from '../lib/api';

interface AgentTimelineProps {
  events: TraceEvent[];
}

export const AgentTimeline: React.FC<AgentTimelineProps> = ({ events }) => {
  const sortedEvents = [...events].sort((a, b) => new Date(a.ts).getTime() - new Date(b.ts).getTime());

  const formatLatency = (ms?: number) => {
    if (ms === undefined) return '';
    return ms > 1000 ? `${(ms / 1000).toFixed(2)}s` : `${ms}ms`;
  };

  const getEventEmoji = (type: string, agent: string) => {
    if (type.includes('start')) return '⚡';
    if (agent === 'security') return '🛡️';
    if (agent === 'quality') return '✨';
    if (agent === 'tests') return '🧪';
    if (agent === 'docs') return '📝';
    if (agent === 'aggregator') return '🤝';
    return '⚙️';
  };

  return (
    <div style={{ padding: '0.5rem 0' }}>
      <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <span>🕵️</span> Execution Trace Timeline
      </h3>
      {sortedEvents.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontSize: '0.9rem', fontStyle: 'italic' }}>
          No trace events logged for this review task.
        </div>
      ) : (
        <div style={{ position: 'relative', borderLeft: '2px solid var(--panel-border)', marginLeft: '1rem', paddingLeft: '1.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {sortedEvents.map((evt) => (
            <div key={evt.id} style={{ position: 'relative' }}>
              {/* Event node indicator */}
              <span style={{
                position: 'absolute',
                left: '-2.25rem',
                top: '0',
                backgroundColor: 'var(--background)',
                border: '2px solid var(--panel-border)',
                borderRadius: '50%',
                width: '1.5rem',
                height: '1.5rem',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '0.8rem',
              }}>
                {getEventEmoji(evt.event_type, evt.agent)}
              </span>

              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.25rem' }}>
                <span style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--foreground)' }}>
                  {evt.agent.toUpperCase()} Agent • {evt.event_type}
                </span>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {new Date(evt.ts).toLocaleTimeString()}
                </span>
              </div>

              {/* Event Details */}
              <div style={{ padding: '0.75rem', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '6px', border: '1px solid var(--panel-border)', fontSize: '0.85rem' }}>
                {evt.model && <div style={{ marginBottom: '0.25rem' }}>Model: <code style={{ color: '#a78bfa' }}>{evt.model}</code></div>}
                
                {evt.latency_ms !== undefined && evt.latency_ms > 0 && (
                  <div style={{ marginBottom: '0.25rem' }}>
                    Latency: <strong>{formatLatency(evt.latency_ms)}</strong>
                  </div>
                )}
                
                {evt.tokens_in !== undefined && (
                  <div style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                    Tokens: {evt.tokens_in} in / {evt.tokens_out} out • Cost: ${evt.cost_usd?.toFixed(4)}
                  </div>
                )}
                
                {evt.outcome && (
                  <div style={{ marginTop: '0.25rem' }}>
                    Status: <span style={{ color: evt.outcome === 'success' ? 'var(--success)' : 'var(--error)' }}>{evt.outcome}</span>
                    {evt.confidence !== undefined && ` • Confidence: ${(evt.confidence * 100).toFixed(0)}%`}
                  </div>
                )}

                {evt.payload && Object.keys(evt.payload).length > 0 && (
                  <div style={{ marginTop: '0.5rem', borderTop: '1px dashed var(--panel-border)', paddingTop: '0.5rem' }}>
                    <details>
                      <summary style={{ cursor: 'pointer', color: 'var(--primary)', outline: 'none' }}>View Payload</summary>
                      <pre style={{
                        marginTop: '0.25rem',
                        padding: '0.5rem',
                        backgroundColor: '#070a13',
                        color: '#9ca3af',
                        fontSize: '0.75rem',
                        borderRadius: '4px',
                        overflowX: 'auto',
                        fontFamily: 'var(--font-mono)',
                      }}>
                        {JSON.stringify(evt.payload, null, 2)}
                      </pre>
                    </details>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
