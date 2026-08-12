'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  FileSearch, DollarSign, CheckCircle2, AlertTriangle, ArrowUpRight, ListChecks,
} from 'lucide-react';
import { api, ReviewRecord, FindingRecord } from '../lib/api';
import { ReviewList } from '../components/ReviewList';
import { FindingCard } from '../components/FindingCard';
import { StatCard } from '../components/StatCard';
import { PageSkeleton } from '../components/Skeleton';
import Link from 'next/link';

const mockReviews: ReviewRecord[] = [
  {
    id: 'golden-001-injection',
    repo: 'owner/repo',
    pr_number: 101,
    created_at: new Date().toISOString(),
    status: 'request_changes',
    summary: '### PR Review Summary\n\nIdentified a potential SQL Injection security flaw. Please parameterize the database query.',
    total_cost_usd: 0.0124,
    total_tokens: 1540,
  },
  {
    id: 'golden-002-missing-test',
    repo: 'owner/repo',
    pr_number: 102,
    created_at: new Date(Date.now() - 3600000).toISOString(),
    status: 'approve',
    summary: '### PR Review Summary\n\nCode looks great. A utility method was added. We recommend adding a corresponding unit test.',
    total_cost_usd: 0.0086,
    total_tokens: 920,
  },
];

const mockFindings: Record<string, FindingRecord[]> = {
  'golden-001-injection': [
    {
      id: 'f1', review_id: 'golden-001-injection', file_path: 'src/db.py',
      line_start: 11, line_end: 13, severity: 'CRITICAL',
      description: 'SQL Injection vulnerability due to direct string concatenation of user input in query builder.',
      confidence: 0.95, created_at: new Date().toISOString(),
    },
  ],
  'golden-002-missing-test': [
    {
      id: 'f2', review_id: 'golden-002-missing-test', file_path: 'src/utils.py',
      line_start: 1, line_end: 6, severity: 'LOW',
      description: 'New utility parse_date has been introduced without unit test coverage. Consider writing assertions.',
      confidence: 0.85, created_at: new Date().toISOString(),
    },
  ],
};

export default function ReviewsPage() {
  const [reviews, setReviews] = React.useState<ReviewRecord[]>([]);
  const [selectedReview, setSelectedReview] = React.useState<ReviewRecord | null>(null);
  const [findings, setFindings] = React.useState<FindingRecord[]>([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getReviews();
        setReviews(data);
        if (data.length > 0) setSelectedReview(data[0]);
      } catch (err) {
        console.warn('API connection failed. Loading local mock datasets.', err);
        setReviews(mockReviews);
        setSelectedReview(mockReviews[0]);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  React.useEffect(() => {
    if (!selectedReview) return;
    const reviewId = selectedReview.id;
    async function loadFindings() {
      try {
        const data = await api.getReviewFindings(reviewId);
        setFindings(data);
      } catch (err) {
        setFindings(mockFindings[reviewId] || []);
      }
    }
    loadFindings();
  }, [selectedReview]);

  const handleFeedbackSubmit = async (index: number, feedbackType: string) => {
    alert(`Feedback submitted: ${feedbackType} on finding #${index + 1}`);
  };

  const handleDisputeSubmit = async (index: number) => {
    alert(`Dispute submitted successfully for finding #${index + 1}`);
  };

  if (loading) {
    return <PageSkeleton label="Loading review dashboard…" />;
  }

  const totalCost = reviews.reduce((s, r) => s + (r.total_cost_usd || 0), 0);
  const approvedCount = reviews.filter((r) => r.status?.toLowerCase() === 'approve').length;
  const flaggedCount = reviews.filter((r) => r.status?.toLowerCase() !== 'approve').length;

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
            <span className="page-title-icon"><FileSearch size={20} /></span>
            <span className="text-gradient">Review Reports</span>
          </h1>
          <p>Inspect automated specialist reviews, track token budget costs, and rate output findings.</p>
        </div>
      </motion.div>

      <div className="stats-grid">
        <StatCard icon={<ListChecks size={18} />} label="Total Reviews" value={reviews.length} accent="var(--primary-2)" delay={0} />
        <StatCard icon={<DollarSign size={18} />} label="Total Spend" value={totalCost} format={(v) => `$${v.toFixed(4)}`} accent="var(--accent-amber)" delay={0.05} />
        <StatCard icon={<CheckCircle2 size={18} />} label="Approved" value={approvedCount} accent="var(--success)" delay={0.1} />
        <StatCard icon={<AlertTriangle size={18} />} label="Flagged" value={flaggedCount} accent="var(--warning)" delay={0.15} />
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem', alignItems: 'flex-start' }}>
        <div>
          <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-muted)' }}>Recent Executions</h3>
          <ReviewList
            reviews={reviews}
            selectedId={selectedReview?.id}
            onSelectReview={(r) => setSelectedReview(r)}
          />
        </div>

        <div>
          <AnimatePresence mode="wait">
            {selectedReview ? (
              <motion.div
                key={selectedReview.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.35, ease: [0.16, 1, 0.3, 1] }}
                style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}
              >
                <div className="card" style={{ borderLeft: '3px solid var(--primary)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '1rem', gap: '1rem', flexWrap: 'wrap' }}>
                    <div>
                      <h2 style={{ fontSize: '1.3rem' }}>{selectedReview.repo}</h2>
                      <p style={{ fontSize: '0.82rem' }}>PR #{selectedReview.pr_number} &middot; Review ID: <code>{selectedReview.id}</code></p>
                    </div>
                    <Link href={`/trace/${selectedReview.id}`} className="btn btn-secondary" style={{ fontSize: '0.8rem' }}>
                      View Trace <ArrowUpRight size={14} />
                    </Link>
                  </div>

                  <div style={{ color: 'var(--foreground)', marginBottom: '1.5rem', whiteSpace: 'pre-wrap', fontSize: '0.92rem', lineHeight: '1.65' }}>
                    {selectedReview.summary || 'No review summary output.'}
                  </div>

                  <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.83rem', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
                    <div>Cost: <strong style={{ color: '#fff' }}>${selectedReview.total_cost_usd.toFixed(4)}</strong></div>
                    <div>Tokens: <strong style={{ color: '#fff' }}>{selectedReview.total_tokens}</strong></div>
                    <div>Status: <strong style={{ color: selectedReview.status === 'approve' ? 'var(--success)' : 'var(--warning)' }}>{selectedReview.status.replace('_', ' ').toUpperCase()}</strong></div>
                  </div>
                </div>

                <div>
                  <h3 style={{ fontSize: '1rem', marginBottom: '1rem', color: 'var(--text-muted)' }}>
                    Detailed Specialist Findings ({findings.length})
                  </h3>
                  {findings.length === 0 ? (
                    <div className="card" style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
                      No specific vulnerability or quality findings reported.
                    </div>
                  ) : (
                    findings.map((finding, idx) => (
                      <FindingCard
                        key={finding.id}
                        finding={finding}
                        index={idx}
                        onFeedbackSubmit={handleFeedbackSubmit}
                        onDisputeSubmit={handleDisputeSubmit}
                      />
                    ))
                  )}
                </div>
              </motion.div>
            ) : (
              <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--text-muted)' }}>
                Select a review execution from the list to display details.
              </div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </main>
  );
}
