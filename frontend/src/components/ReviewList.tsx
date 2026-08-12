import React from 'react';
import { motion } from 'framer-motion';
import { CheckCircle2, XCircle, AlertTriangle, GitPullRequest, Inbox } from 'lucide-react';
import { ReviewRecord } from '../lib/api';

interface ReviewListProps {
  reviews: ReviewRecord[];
  selectedId?: string;
  onSelectReview: (review: ReviewRecord) => void;
}

const STATUS_META: Record<string, { color: string; bg: string; icon: React.ElementType }> = {
  approve: { color: 'var(--success)', bg: 'var(--success-bg)', icon: CheckCircle2 },
  request_changes: { color: 'var(--error)', bg: 'var(--error-bg)', icon: XCircle },
  escalate_to_human: { color: 'var(--warning)', bg: 'var(--warning-bg)', icon: AlertTriangle },
};

function metaFor(status?: string) {
  if (!status) return { color: 'var(--text-muted)', bg: 'rgba(255,255,255,0.05)', icon: GitPullRequest };
  return STATUS_META[status.toLowerCase()] || { color: 'var(--text-muted)', bg: 'rgba(255,255,255,0.05)', icon: GitPullRequest };
}

export const ReviewList: React.FC<ReviewListProps> = ({ reviews, selectedId, onSelectReview }) => {
  if (reviews.length === 0) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '3rem 1.5rem', color: 'var(--text-muted)' }}>
        <Inbox size={28} style={{ marginBottom: '0.75rem', opacity: 0.5 }} />
        <div style={{ fontSize: '0.9rem' }}>No review records found. We&apos;ll show reviews as soon as a webhook triggers execution.</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      {reviews.map((r, idx) => {
        const isSelected = selectedId === r.id;
        const { color, bg, icon: Icon } = metaFor(r.status);
        return (
          <motion.div
            key={r.id}
            layout
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
            whileHover={{ x: 3 }}
            className="card"
            style={{
              padding: '0.9rem 1.1rem',
              cursor: 'pointer',
              borderColor: isSelected ? 'var(--primary)' : 'var(--panel-border)',
              background: isSelected
                ? 'linear-gradient(135deg, rgba(124,107,247,0.10), rgba(124,107,247,0.02))'
                : 'var(--panel-bg)',
              boxShadow: isSelected ? 'var(--shadow-glow)' : 'var(--shadow-sm)',
            }}
            onClick={() => onSelectReview(r)}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '0.75rem' }}>
              <div style={{ minWidth: 0 }}>
                <h4 style={{ fontSize: '0.9rem', marginBottom: '0.2rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.repo}
                </h4>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  PR #{r.pr_number} &middot; {new Date(r.created_at).toLocaleDateString()}
                </p>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexShrink: 0 }}>
                <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', fontVariantNumeric: 'tabular-nums' }}>
                  ${r.total_cost_usd.toFixed(4)}
                </span>
                <span className="badge" style={{ backgroundColor: bg, color }}>
                  <Icon size={11} strokeWidth={2.5} />
                  {r.status.replace('_', ' ')}
                </span>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  );
};
