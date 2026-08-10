'use client';

import React from 'react';
import { api, HitlItem } from '../../lib/api';

export default function HitlQueuePage() {
  const [items, setItems] = React.useState<HitlItem[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [reviewerName, setReviewerName] = React.useState('Reviewer One');
  const [comments, setComments] = React.useState('');

  const mockHitlItems: HitlItem[] = [
    {
      id: 'hitl-item-1',
      review_id: 'golden-001-injection',
      escalated_at: new Date().toISOString(),
      status: 'pending',
      reason: 'CRITICAL finding: SQL injection detected in src/db.py',
    }
  ];

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
      setItems(items.map(item => item.id === itemId ? { ...item, status: 'claimed', claimed_by: reviewerName } : item));
    } catch (err) {
      // Offline fallback simulation
      setItems(items.map(item => item.id === itemId ? { ...item, status: 'claimed', claimed_by: reviewerName } : item));
    }
  };

  const handleResolve = async (itemId: string, decision: 'APPROVE' | 'REJECT') => {
    try {
      await api.resolveHitlItem(itemId, decision, reviewerName, comments);
      setItems(items.filter(item => item.id !== itemId));
      setComments('');
      alert(`Review item resolved with decision: ${decision}`);
    } catch (err) {
      // Offline fallback simulation
      setItems(items.filter(item => item.id !== itemId));
      setComments('');
      alert(`Review item resolved (simulated offline) with decision: ${decision}`);
    }
  };

  if (loading) {
    return (
      <div className="main-container" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '50vh' }}>
        <div style={{ fontSize: '1.2rem', color: 'var(--text-muted)' }}>Loading HITL Queue...</div>
      </div>
    );
  }

  return (
    <main className="main-container">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <div>
          <h1 style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>🧑‍⚖️ Human-in-the-loop Queue</h1>
          <p>Authorize critical security flags or low-confidence reviews before they are posted to GitHub.</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <label style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Reviewer Identity:</label>
          <input
            type="text"
            className="card"
            style={{ padding: '0.4rem 0.75rem', borderRadius: '6px', fontSize: '0.9rem', width: '180px', margin: 0 }}
            value={reviewerName}
            onChange={(e) => setReviewerName(e.target.value)}
          />
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
        {items.length === 0 ? (
          <div className="card" style={{ textAlign: 'center', padding: '4rem 2rem', color: 'var(--text-muted)' }}>
            🎉 Hurrah! The HITL review queue is completely empty.
          </div>
        ) : (
          items.map((item) => (
            <div key={item.id} className="card" style={{ borderLeft: '4px solid var(--warning)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1rem', borderBottom: '1px solid var(--panel-border)', paddingBottom: '1rem' }}>
                <div>
                  <h3 style={{ fontSize: '1.1rem', marginBottom: '0.25rem' }}>Review Job Escalation</h3>
                  <p style={{ fontSize: '0.85rem' }}>
                    Review ID: <code>{item.review_id}</code> • Escalated: {new Date(item.escalated_at).toLocaleString()}
                  </p>
                </div>
                <span className="badge badge-pending">{item.status}</span>
              </div>

              <div style={{ marginBottom: '1.5rem' }}>
                <strong style={{ display: 'block', fontSize: '0.9rem', color: '#a78bfa', marginBottom: '0.25rem' }}>REASON FOR ESCALATION:</strong>
                <p style={{ color: 'var(--foreground)', fontSize: '0.95rem' }}>{item.reason}</p>
              </div>

              {item.status === 'pending' ? (
                <button className="btn btn-primary" onClick={() => handleClaim(item.id)}>
                  Claim Review Task
                </button>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                  <div style={{ fontSize: '0.9rem', color: 'var(--text-muted)' }}>
                    Claimed by: <strong>{item.claimed_by}</strong>
                  </div>
                  <div>
                    <label style={{ display: 'block', fontSize: '0.85rem', marginBottom: '0.5rem', fontWeight: 600 }}>Reviewer Decision Comments:</label>
                    <textarea
                      style={{ width: '100%', padding: '0.75rem', borderRadius: '8px', backgroundColor: '#1f2937', border: '1px solid var(--panel-border)', color: '#fff', fontSize: '0.9rem' }}
                      placeholder="Explain your decision..."
                      value={comments}
                      onChange={(e) => setComments(e.target.value)}
                      rows={3}
                    />
                  </div>
                  <div style={{ display: 'flex', gap: '1rem' }}>
                    <button className="btn btn-primary" onClick={() => handleResolve(item.id, 'APPROVE')}>
                      ✅ Approve Review
                    </button>
                    <button className="btn btn-secondary" style={{ borderColor: 'var(--error)', color: 'var(--error)' }} onClick={() => handleResolve(item.id, 'REJECT')}>
                      ❌ Reject & Block PR
                    </button>
                  </div>
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </main>
  );
}
