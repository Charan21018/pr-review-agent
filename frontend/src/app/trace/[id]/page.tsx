'use client';

import React from 'react';
import { api, TraceEvent } from '../../../lib/api';
import { AgentTimeline } from '../../../components/AgentTimeline';
import Link from 'next/link';

interface TracePageProps {
  params: Promise<{ id: string }>;
}

export default function TracePage({ params }: TracePageProps) {
  const resolvedParams = React.use(params);
  const reviewId = resolvedParams.id;

  const [events, setEvents] = React.useState<TraceEvent[]>([]);
  const [loading, setLoading] = React.useState(true);

  const mockEvents: TraceEvent[] = [
    {
      id: 'e1',
      ts: new Date(Date.now() - 15000).toISOString(),
      review_id: reviewId,
      agent: 'retriever',
      event_type: 'span.start',
      span_id: 's1',
      payload: { query: 'SQL queries file context' }
    },
    {
      id: 'e2',
      ts: new Date(Date.now() - 12000).toISOString(),
      review_id: reviewId,
      agent: 'retriever',
      event_type: 'span.end',
      span_id: 's1',
      latency_ms: 1200,
      outcome: 'success',
      payload: { chunks_retrieved: 4 }
    },
    {
      id: 'e3',
      ts: new Date(Date.now() - 11000).toISOString(),
      review_id: reviewId,
      agent: 'security',
      event_type: 'llm.call',
      span_id: 's2',
      model: 'gpt-4o-mini',
      tokens_in: 450,
      tokens_out: 250,
      cost_usd: 0.0035,
      latency_ms: 2200,
      outcome: 'success',
      confidence: 0.95,
      payload: { findings_detected: 1 }
    },
    {
      id: 'e4',
      ts: new Date(Date.now() - 8000).toISOString(),
      review_id: reviewId,
      agent: 'aggregator',
      event_type: 'llm.call',
      span_id: 's3',
      model: 'gpt-4o-mini',
      tokens_in: 1200,
      tokens_out: 400,
      cost_usd: 0.0084,
      latency_ms: 3100,
      outcome: 'success',
      payload: { recommendation: 'REQUEST_CHANGES' }
    }
  ];

  React.useEffect(() => {
    async function loadTrace() {
      try {
        const trace = await api.getReviewTrace(reviewId);
        setEvents(trace);
      } catch (err) {
        console.warn('API connection failed. Loading local mock trace events.', err);
        setEvents(mockEvents);
      } finally {
        setLoading(false);
      }
    }
    loadTrace();
  }, [reviewId]);

  if (loading) {
    return (
      <div className="main-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading review execution trace...</div>
      </div>
    );
  }

  return (
    <main className="main-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2.5rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔍 Trace Log Viewer</h1>
          <p>Review ID: <code style={{ color: '#a78bfa' }}>{reviewId}</code></p>
        </div>
        <Link href="/" className="btn btn-secondary">
          ⬅️ Back to Dashboard
        </Link>
      </div>

      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <AgentTimeline events={events} />
      </div>
    </main>
  );
}
