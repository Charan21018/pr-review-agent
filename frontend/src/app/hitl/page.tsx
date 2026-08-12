'use client';

import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Gavel, PartyPopper, UserCheck, Check, X } from 'lucide-react';
import { api, HitlItem } from '../../lib/api';
import { PageSkeleton } from '../../components/Skeleton';

const mockHitlItems: HitlItem[] = [
  {
    id: 'hitl-item-1',
    review_id: 'golden-001-injection',
    escalated_at: new Date().toISOString(),
    status: 'pending',
    reason: 'CRITICAL finding: SQL injection detected in src/db.py',
  },
];

export default function HitlQueuePage() {
  const [items, setItems] = React.useState<HitlItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [reviewerName, setReviewerName] = React.useState('Reviewer One');
  const [comments, setComments] = React.useState('');

  React.useEffect(() => {
    async function loadQueue() {
      try {
        const data = await api.getHitlQueue();
        setItems(data);
      } catch (err) {
        console.warn('API connection failed. Loading local mock HITL items.', err);
        setItems(mockHitlItems);
      } finally {
        setLoading(false);
      }
    }
    loadQueue();
  }, []);

  const handleClaim = async (itemId: string) => {
    try {
      await api.claimHitlItem(itemId, reviewerName);
    } catch (err) {
      // Offline fallback simulation
    } finally {
      setItems((prev) => prev.map((item) => (item.id === itemId ? { ...item, status: 'claimed', claimed_by: reviewerName } : item)));
    }
  };

  const handleResolve = async (itemId: string, decision: 'APPROVE' | 'REJECT') => {
    try {
      await api.resolveHitlItem(itemId, decision, reviewerName, comments);
    } catch (err) {
      // Offline fallback simulation
    } finally {
      setItems((prev) => prev.filter((item) => item.id !== itemId));
      setComments('');
    }
  };

  if (loading) {
    return <PageSkeleton label="Loading HITL queue…" />;
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
            <span className="page-title-icon"><Gavel size={20} /></span>
            <span className="text-gradient">Human-in-the-Loop Queue</span>
          </h1>
          <p>Authorize critical security flags or low-confidence reviews before they are posted to GitHub.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
          <UserCheck size={16} color="var(--text-muted)" />
          <input
            type="text"
            className="glass-input"
            style={{ width: 180 }}
            value={reviewerName}
            onChange={(e) => setReviewerName(e.target.value)}
          />
        </div>
      </motion.div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        <AnimatePresence mode="popLayout">
          {items.length === 0 ? (
            <motion.div
              key="empty"
              initial={{ opacity: 0, scale: 0.96 }}
              animate={{ opacity: 1, scale: 1 }}
              className="card"
              style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--text-muted)' }}
            >
              <PartyPopper size={30} style={{ marginBottom: '0.75rem', opacity: 0.7 }} />
              <div>The HITL review queue is completely empty.</div>
            </motion.div>
          ) : (
            items.map((item, idx) => (
              <motion.div
                key={item.id}
                layout
                initial={{ opacity: 0, y: 16 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, transition: { duration: 0.25 } }}
                transition={{ delay: idx * 0.06, duration: 0.4, ease: [0.16, 1, 0.3, 1] }}
                className="card"
                style={{ borderLeft: '3px solid var(--warning)' }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '1rem', gap: '1rem', flexWrap: 'wrap' }}>
                  <div>
                    <h3 style={{ fontSize: '1.05rem', marginBottom: '0.25rem' }}>Review Job Escalation</h3>
                    <p style={{ fontSize: '0.82rem' }}>
                      Review ID: <code>{item.review_id}</code> &middot; Escalated: {new Date(item.escalated_at).toLocaleString()}
                    </p>
                  </div>
                  <span className="badge badge-pending">{item.status}</span>
                </div>

                <div style={{ marginBottom: '1.5rem' }}>
                  <strong style={{ display: 'block', fontSize: '0.85rem', color: 'var(--primary-2)', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '0.03em' }}>
                    Reason for Escalation
                  </strong>
                  <p style={{ color: 'var(--foreground)', fontSize: '0.92rem' }}>{item.reason}</p>
                </div>

                {item.status === 'pending' ? (
                  <button className="btn btn-primary" onClick={() => handleClaim(item.id)}>
                    Claim Review Task
                  </button>
                ) : (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}
                  >
                    <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                      Claimed by: <strong style={{ color: 'var(--foreground)' }}>{item.claimed_by}</strong>
                    </div>
                    <div>
                      <label style={{ display: 'block', fontSize: '0.82rem', marginBottom: '0.5rem', fontWeight: 600 }}>Reviewer Decision Comments</label>
                      <textarea
                        className="glass-input"
                        style={{ width: '100%' }}
                        placeholder="Explain your decision..."
                        value={comments}
                        onChange={(e) => setComments(e.target.value)}
                        rows={3}
                      />
                    </div>
                    <div style={{ display: 'flex', gap: '0.85rem', flexWrap: 'wrap' }}>
                      <button className="btn btn-primary" onClick={() => handleResolve(item.id, 'APPROVE')}>
                        <Check size={15} /> Approve Review
                      </button>
                      <button
                        className="btn btn-secondary"
                        style={{ borderColor: 'rgba(251,113,133,0.35)', color: 'var(--error)' }}
                        onClick={() => handleResolve(item.id, 'REJECT')}
                      >
                        <X size={15} /> Reject &amp; Block PR
                      </button>
                    </div>
                  </motion.div>
                )}
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>
    </main>
  );
}
