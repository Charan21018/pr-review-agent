import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ShieldAlert, AlertTriangle, AlertCircle, Info, ThumbsUp, Flag, Send,
} from 'lucide-react';
import { FindingRecord } from '../lib/api';

interface FindingCardProps {
  finding: FindingRecord;
  index: number;
  onFeedbackSubmit?: (index: number, feedbackType: string, comment: string) => void;
  onDisputeSubmit?: (index: number, reason: string) => void;
}

const SEVERITY_META: Record<string, { color: string; bg: string; icon: React.ElementType }> = {
  CRITICAL: { color: '#fb7185', bg: 'rgba(251,113,133,0.12)', icon: ShieldAlert },
  HIGH: { color: '#fb923c', bg: 'rgba(251,146,60,0.12)', icon: AlertTriangle },
  MEDIUM: { color: '#fbbf24', bg: 'rgba(251,191,36,0.12)', icon: AlertCircle },
  LOW: { color: '#38bdf8', bg: 'rgba(56,189,248,0.12)', icon: Info },
};

function metaFor(sev: string) {
  return SEVERITY_META[sev.toUpperCase()] || { color: '#34d399', bg: 'rgba(52,211,153,0.12)', icon: Info };
}

export const FindingCard: React.FC<FindingCardProps> = ({
  finding, index, onFeedbackSubmit, onDisputeSubmit,
}) => {
  const [feedbackComment, setFeedbackComment] = React.useState('');
  const [disputeReason, setDisputeReason] = React.useState('');
  const [showFeedbackForm, setShowFeedbackForm] = React.useState(false);
  const [showDisputeForm, setShowDisputeForm] = React.useState(false);

  const { color, bg, icon: Icon } = metaFor(finding.severity);

  const submitFeedback = (feedbackType: string) => {
    if (!onFeedbackSubmit) return;
    onFeedbackSubmit(index, feedbackType, feedbackComment);
    setFeedbackComment('');
    setShowFeedbackForm(false);
  };

  const handleCommentKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submitFeedback('comment');
    }
  };

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.06, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
      className="card card-hover"
      style={{ marginBottom: '1rem', borderLeft: `3px solid ${color}` }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
          <span className="badge" style={{ backgroundColor: bg, color }}>
            <Icon size={11} strokeWidth={2.5} />
            {finding.severity}
          </span>
          <code style={{ fontSize: '0.85rem', color: 'var(--primary-2)' }}>
            {finding.file_path}
            {finding.line_start && ` : L${finding.line_start}${finding.line_end ? `-L${finding.line_end}` : ''}`}
          </code>
        </div>
        <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', flexShrink: 0 }}>
          Confidence: <strong style={{ color: finding.confidence >= 0.8 ? 'var(--success)' : 'var(--warning)' }}>{(finding.confidence * 100).toFixed(0)}%</strong>
        </div>
      </div>

      <p style={{ color: 'var(--foreground)', marginBottom: '1rem', whiteSpace: 'pre-wrap', fontSize: '0.9rem' }}>
        {finding.description}
      </p>

      <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
        <button
          className="btn btn-secondary"
          style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem' }}
          onClick={() => { setShowFeedbackForm((v) => !v); setShowDisputeForm(false); }}
        >
          <ThumbsUp size={13} /> Rate Finding
        </button>
        <button
          className="btn btn-secondary"
          style={{ padding: '0.35rem 0.75rem', fontSize: '0.78rem', borderColor: 'rgba(251,113,133,0.3)' }}
          onClick={() => { setShowDisputeForm((v) => !v); setShowFeedbackForm(false); }}
        >
          <Flag size={13} /> Dispute Finding
        </button>
      </div>

      <AnimatePresence initial={false}>
        {showFeedbackForm && onFeedbackSubmit && (
          <motion.div
            key="feedback"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '10px', border: '1px solid var(--panel-border)' }}>
              <h4 style={{ fontSize: '0.82rem', marginBottom: '0.6rem' }}>Submit Feedback</h4>
              <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem', alignItems: 'flex-start' }}>
                <textarea
                  className="glass-input"
                  style={{ width: '100%', resize: 'vertical' }}
                  placeholder="Add optional comments... (Enter to submit, Shift+Enter for a new line)"
                  value={feedbackComment}
                  onChange={(e) => setFeedbackComment(e.target.value)}
                  onKeyDown={handleCommentKeyDown}
                  rows={2}
                />
                <button
                  className="btn btn-primary"
                  style={{ padding: '0.5rem 0.75rem', fontSize: '0.78rem', flexShrink: 0 }}
                  onClick={() => submitFeedback('comment')}
                  title="Submit comment (Enter)"
                >
                  <Send size={13} />
                </button>
              </div>
              <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }} onClick={() => submitFeedback('true_positive')}>True Positive</button>
                <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }} onClick={() => submitFeedback('false_positive')}>False Positive</button>
                <button className="btn btn-secondary" style={{ padding: '0.3rem 0.6rem', fontSize: '0.72rem' }} onClick={() => submitFeedback('unhelpful')}>Unhelpful</button>
              </div>
            </div>
          </motion.div>
        )}

        {showDisputeForm && onDisputeSubmit && (
          <motion.div
            key="dispute"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
            style={{ overflow: 'hidden' }}
          >
            <div style={{ marginTop: '1rem', padding: '1rem', background: 'rgba(251,113,133,0.03)', borderRadius: '10px', border: '1px solid rgba(251,113,133,0.2)' }}>
              <h4 style={{ fontSize: '0.82rem', marginBottom: '0.6rem', color: '#fb7185' }}>Submit Dispute Request</h4>
              <textarea
                className="glass-input"
                style={{ width: '100%', marginBottom: '0.6rem' }}
                placeholder="Provide justification why this finding is incorrect..."
                value={disputeReason}
                onChange={(e) => setDisputeReason(e.target.value)}
                rows={3}
              />
              <button
                className="btn btn-primary"
                style={{ background: 'linear-gradient(135deg, #fb7185, #f43f5e)', padding: '0.4rem 0.85rem', fontSize: '0.78rem' }}
                onClick={() => { onDisputeSubmit(index, disputeReason); setShowDisputeForm(false); }}
              >
                Submit Dispute
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};
