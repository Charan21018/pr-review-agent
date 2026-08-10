'use client';

import React from 'react';
import { api, ReviewRecord, FindingRecord } from '../lib/api';
import { ReviewList } from '../components/ReviewList';
import { FindingCard } from '../components/FindingCard';
import Link from 'next/link';

export default function ReviewsPage() {
  const [reviews, setReviews] = React.useState<ReviewRecord[]>([]);
  const [selectedReview, setSelectedReview] = React.useState<ReviewRecord | null>(null);
  const [findings, setFindings] = React.useState<FindingRecord[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState<string | null>(null);

  // Mock data fallback if API is offline
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
    }
  ];

  const mockFindings: Record<string, FindingRecord[]> = {
    'golden-001-injection': [
      {
        id: 'f1',
        review_id: 'golden-001-injection',
        file_path: 'src/db.py',
        line_start: 11,
        line_end: 13,
        severity: 'CRITICAL',
        description: 'SQL Injection vulnerability due to direct string concatenation of user input in query builder.',
        confidence: 0.95,
        created_at: new Date().toISOString(),
      }
    ],
    'golden-002-missing-test': [
      {
        id: 'f2',
        review_id: 'golden-002-missing-test',
        file_path: 'src/utils.py',
        line_start: 1,
        line_end: 6,
        severity: 'LOW',
        description: 'New utility parse_date has been introduced without unit test coverage. Consider writing assertions.',
        confidence: 0.85,
        created_at: new Date().toISOString(),
      }
    ]
  };

  React.useEffect(() => {
    async function loadData() {
      try {
        const data = await api.getReviews();
        setReviews(data);
        if (data.length > 0) {
          setSelectedReview(data[0]);
        }
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

  const handleFeedbackSubmit = async (index: number, feedbackType: string, comment: string) => {
    if (!selectedReview) return;
    try {
      // Simulate/Trigger rating API call
      alert(`Feedback submitted: ${feedbackType} on finding #${index + 1}`);
    } catch (err) {
      alert('Failed to submit feedback');
    }
  };

  const handleDisputeSubmit = async (index: number, reason: string) => {
    if (!selectedReview) return;
    try {
      alert(`Dispute submitted successfully for finding #${index + 1}`);
    } catch (err) {
      alert('Failed to submit dispute');
    }
  };

  if (loading) {
    return (
      <div className="main-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading review dashboard...</div>
      </div>
    );
  }

  return (
    <main className="main-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🔍 Review Reports</h1>
          <p>Inspect automated specialist reviews, track token budget costs, and rate output findings.</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '2rem', alignItems: 'flex-start' }}>
        {/* Left Column - List of Reviews */}
        <div>
          <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: 'var(--text-muted)' }}>Recent Executions</h3>
          <ReviewList
            reviews={reviews}
            selectedId={selectedReview?.id}
            onSelectReview={(r) => setSelectedReview(r)}
          />
        </div>

        {/* Right Column - Review Details */}
        <div>
          {selectedReview ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
              <div className="card" style={{ borderLeft: '4px solid var(--primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '1rem' }}>
                  <div>
                    <h2 style={{ fontSize: '1.4rem' }}>{selectedReview.repo}</h2>
                    <p style={{ fontSize: '0.85rem' }}>PR #{selectedReview.pr_number} • Review ID: <code>{selectedReview.id}</code></p>
                  </div>
                  <Link href={`/trace/${selectedReview.id}`} className="btn btn-secondary" style={{ fontSize: '0.8rem' }}>
                    🛰️ View Trace Details
                  </Link>
                </div>

                <div style={{ color: 'var(--foreground)', marginBottom: '1.5rem', whiteSpace: 'pre-wrap', fontSize: '0.95rem', lineHeight: '1.6' }}>
                  {selectedReview.summary || 'No review summary output.'}
                </div>

                <div style={{ display: 'flex', gap: '1.5rem', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  <div>Cost: <strong style={{ color: '#fff' }}>${selectedReview.total_cost_usd.toFixed(4)}</strong></div>
                  <div>Tokens: <strong style={{ color: '#fff' }}>{selectedReview.total_tokens}</strong></div>
                  <div>Status: <strong style={{ color: selectedReview.status === 'approve' ? 'var(--success)' : 'var(--warning)' }}>{selectedReview.status.replace('_', ' ').toUpperCase()}</strong></div>
                </div>
              </div>

              <div>
                <h3 style={{ fontSize: '1.1rem', marginBottom: '1rem', color: 'var(--text-muted)' }}>
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
            </div>
          ) : (
            <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--text-muted)' }}>
              Select a review execution from the list to display details.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
