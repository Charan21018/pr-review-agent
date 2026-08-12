'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Radar, ArrowLeft } from 'lucide-react';
import { api, TraceEvent } from '../../../lib/api';
import { AgentTimeline } from '../../../components/AgentTimeline';
import { Skeleton } from '../../../components/Skeleton';
import Link from 'next/link';

interface TracePageProps {
  params: Promise<{ id: string }>;
}

const mockEventsFor = (reviewId: string): TraceEvent[] => [
  {
    id: 'e1', ts: new Date(Date.now() - 15000).toISOString(), review_id: reviewId,
    agent: 'retriever', event_type: 'span.start', span_id: 's1',
    payload: { query: 'SQL queries file context' },
  },
  {
    id: 'e2', ts: new Date(Date.now() - 12000).toISOString(), review_id: reviewId,
    agent: 'retriever', event_type: 'span.end', span_id: 's1',
    latency_ms: 1200, outcome: 'success', payload: { chunks_retrieved: 4 },
  },
  {
    id: 'e3', ts: new Date(Date.now() - 11000).toISOString(), review_id: reviewId,
    agent: 'security', event_type: 'llm.call', span_id: 's2', model: 'gemini-2.5-flash',
    tokens_in: 450, tokens_out: 250, cost_usd: 0.0035, latency_ms: 2200,
    outcome: 'success', confidence: 0.95, payload: { findings_detected: 1 },
  },
  {
    id: 'e4', ts: new Date(Date.now() - 8000).toISOString(), review_id: reviewId,
    agent: 'aggregator', event_type: 'llm.call', span_id: 's3', model: 'gemini-2.5-flash',
    tokens_in: 1200, tokens_out: 400, cost_usd: 0.0084, latency_ms: 3100,
    outcome: 'success', payload: { recommendation: 'REQUEST_CHANGES' },
  },
];

export default function TracePage({ params }: TracePageProps) {
  const resolvedParams = React.use(params);
  const reviewId = resolvedParams.id;

  const [events, setEvents] = React.useState<TraceEvent[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    async function loadTrace() {
      try {
        const trace = await api.getReviewTrace(reviewId);
        setEvents(trace);
      } catch (err) {
        console.warn('API connection failed. Loading local mock trace events.', err);
        setEvents(mockEventsFor(reviewId));
      } finally {
        setLoading(false);
      }
    }
    loadTrace();
  }, [reviewId]);

  if (loading) {
    return (
      <div className="main-container">
        <Skeleton width={260} height={30} radius="8px" style={{ marginBottom: '0.6rem' }} />
        <Skeleton width={320} height={16} radius="6px" style={{ marginBottom: '2.5rem' }} />
        <div style={{ maxWidth: 800, margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
          {[0, 1, 2].map((i) => <Skeleton key={i} height={90} radius="16px" />)}
        </div>
      </div>
    );
  }

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
            <span className="page-title-icon"><Radar size={20} /></span>
            <span className="text-gradient">Trace Log Viewer</span>
          </h1>
          <p>Review ID: <code style={{ color: 'var(--primary-2)' }}>{reviewId}</code></p>
        </div>
        <Link href="/" className="btn btn-secondary">
          <ArrowLeft size={14} /> Back to Dashboard
        </Link>
      </motion.div>

      <div style={{ maxWidth: '800px', margin: '0 auto' }}>
        <AgentTimeline events={events} />
      </div>
    </main>
  );
}
