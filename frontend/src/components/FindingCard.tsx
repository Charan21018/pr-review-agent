import React from 'react';
import { FindingRecord } from '../lib/api';

interface FindingCardProps {
  finding: FindingRecord;
  index: number;
  onFeedbackSubmit?: (index: number, feedbackType: string, comment: string) => void;
  onDisputeSubmit?: (index: number, reason: string) => void;
}

export const FindingCard: React.FC<FindingCardProps> = ({
  finding,
  index,
  onFeedbackSubmit,
  onDisputeSubmit,
}) => {
  const [feedbackComment, setFeedbackComment] = React.useState('');
  const [disputeReason, setDisputeReason] = React.useState('');
  const [showFeedbackForm, setShowFeedbackForm] = React.useState(false);
  const [showDisputeForm, setShowDisputeForm] = React.useState(false);

  const getSeverityColor = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL': return '#ef4444';
      case 'HIGH': return '#f97316';
      case 'MEDIUM': return '#eab308';
      case 'LOW': return '#3b82f6';
      default: return '#10b981';
    }
  };

  const getSeverityBg = (sev: string) => {
    switch (sev.toUpperCase()) {
      case 'CRITICAL': return 'rgba(239, 68, 68, 0.1)';
      case 'HIGH': return 'rgba(249, 115, 22, 0.1)';
      case 'MEDIUM': return 'rgba(234, 179, 8, 0.1)';
      case 'LOW': return 'rgba(59, 130, 246, 0.1)';
      default: return 'rgba(16, 185, 129, 0.1)';
    }
  };

  return (
    <div className="card" style={{ marginBottom: '1.25rem', borderLeft: `4px solid ${getSeverityColor(finding.severity)}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <div>
          <span className="badge" style={{ backgroundColor: getSeverityBg(finding.severity), color: getSeverityColor(finding.severity), marginRight: '0.75rem' }}>
            {finding.severity}
          </span>
          <code style={{ fontSize: '0.9rem', color: '#a78bfa' }}>
            {finding.file_path}
            {finding.line_start && ` : L${finding.line_start}${finding.line_end ? `-L${finding.line_end}` : ''}`}
          </code>
        </div>
        <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
          Confidence: <strong style={{ color: finding.confidence >= 0.8 ? '#10b981' : '#f59e0b' }}>{(finding.confidence * 100).toFixed(0)}%</strong>
        </div>
      </div>

      <p style={{ color: 'var(--foreground)', marginBottom: '1rem', whiteSpace: 'pre-wrap' }}>
        {finding.description}
      </p>

      {/* Action Buttons */}
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '1rem', flexWrap: 'wrap' }}>
        <button 
          className="btn btn-secondary" 
          style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
          onClick={() => { setShowFeedbackForm(!showFeedbackForm); setShowDisputeForm(false); }}
        >
          Rate Finding
        </button>
        <button 
          className="btn btn-secondary" 
          style={{ padding: '0.35rem 0.75rem', fontSize: '0.8rem', borderColor: 'rgba(239, 68, 68, 0.3)' }}
          onClick={() => { setShowDisputeForm(!showDisputeForm); setShowFeedbackForm(false); }}
        >
          Dispute Finding
        </button>
      </div>

      {/* Feedback Form overlay */}
      {showFeedbackForm && onFeedbackSubmit && (
        <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--panel-border)' }}>
          <h4 style={{ fontSize: '0.85rem', marginBottom: '0.5rem' }}>Submit Feedback</h4>
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.5rem' }}>
            <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => onFeedbackSubmit(index, 'true_positive', feedbackComment)}>True Positive</button>
            <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => onFeedbackSubmit(index, 'false_positive', feedbackComment)}>False Positive</button>
            <button className="btn btn-secondary" style={{ padding: '0.25rem 0.5rem', fontSize: '0.75rem' }} onClick={() => onFeedbackSubmit(index, 'unhelpful', feedbackComment)}>Unhelpful</button>
          </div>
          <textarea
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', backgroundColor: '#1f2937', border: '1px solid #374151', color: '#fff', fontSize: '0.85rem' }}
            placeholder="Add optional comments..."
            value={feedbackComment}
            onChange={(e) => setFeedbackComment(e.target.value)}
          />
        </div>
      )}

      {/* Dispute Form overlay */}
      {showDisputeForm && onDisputeSubmit && (
        <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: 'rgba(239,68,68,0.02)', borderRadius: '8px', border: '1px solid rgba(239,68,68,0.2)' }}>
          <h4 style={{ fontSize: '0.85rem', marginBottom: '0.5rem', color: '#ef4444' }}>Submit Dispute Request</h4>
          <textarea
            style={{ width: '100%', padding: '0.5rem', borderRadius: '6px', backgroundColor: '#1f2937', border: '1px solid #374151', color: '#fff', fontSize: '0.85rem', marginBottom: '0.5rem' }}
            placeholder="Provide justification why this finding is incorrect..."
            value={disputeReason}
            onChange={(e) => setDisputeReason(e.target.value)}
            rows={3}
          />
          <button 
            className="btn btn-primary" 
            style={{ backgroundColor: '#ef4444', padding: '0.35rem 0.75rem', fontSize: '0.8rem' }}
            onClick={() => { onDisputeSubmit(index, disputeReason); setShowDisputeForm(false); }}
          >
            Submit Dispute
          </button>
        </div>
      )}
    </div>
  );
};
