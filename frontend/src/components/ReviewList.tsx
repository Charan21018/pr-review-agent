import React from 'react';
import { ReviewRecord } from '../lib/api';

interface ReviewListProps {
  reviews: ReviewRecord[];
  selectedId?: string;
  onSelectReview: (review: ReviewRecord) => void;
}

export const ReviewList: React.FC<ReviewListProps> = ({
  reviews,
  selectedId,
  onSelectReview,
}) => {
  const getRecommendationColor = (rec?: string) => {
    if (!rec) return 'var(--text-muted)';
    switch (rec.toLowerCase()) {
      case 'approve': return 'var(--success)';
      case 'request_changes': return 'var(--error)';
      case 'escalate_to_human': return 'var(--warning)';
      default: return 'var(--text-muted)';
    }
  };

  const getRecommendationBg = (rec?: string) => {
    if (!rec) return 'rgba(255, 255, 255, 0.05)';
    switch (rec.toLowerCase()) {
      case 'approve': return 'var(--success-bg)';
      case 'request_changes': return 'var(--error-bg)';
      case 'escalate_to_human': return 'var(--warning-bg)';
      default: return 'rgba(255, 255, 255, 0.05)';
    }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {reviews.length === 0 ? (
        <div className="card" style={{ textAlign: 'center', padding: '3rem 2rem', color: 'var(--text-muted)' }}>
          No review records found. We'll show reviews as soon as webhook triggers execution.
        </div>
      ) : (
        reviews.map((r) => (
          <div
            key={r.id}
            className="card"
            style={{
              padding: '1rem 1.25rem',
              cursor: 'pointer',
              borderColor: selectedId === r.id ? 'var(--primary)' : 'var(--panel-border)',
              backgroundColor: selectedId === r.id ? 'rgba(99, 102, 241, 0.03)' : 'var(--panel-bg)',
            }}
            onClick={() => onSelectReview(r)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div>
                <h4 style={{ fontSize: '0.95rem', marginBottom: '0.25rem' }}>
                  {r.repo}
                </h4>
                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  PR #{r.pr_number} • {new Date(r.created_at).toLocaleDateString()}
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                <span style={{ fontSize: '0.85rem', color: '#9ca3af' }}>
                  ${r.total_cost_usd.toFixed(4)}
                </span>
                <span
                  className="badge"
                  style={{
                    backgroundColor: getRecommendationBg(r.status),
                    color: getRecommendationColor(r.status),
                    fontSize: '0.7rem',
                  }}
                >
                  {r.status.replace('_', ' ')}
                </span>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );
};
