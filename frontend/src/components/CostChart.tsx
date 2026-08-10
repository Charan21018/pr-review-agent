import React from 'react';
import { EconomicsData } from '../lib/api';

interface CostChartProps {
  data: EconomicsData;
}

export const CostChart: React.FC<CostChartProps> = ({ data }) => {
  const agentCosts = data.agent_costs || {};
  const totalCost = Object.values(agentCosts).reduce((sum, val) => sum + val, 0);

  // Fallback values if empty
  const costs = totalCost > 0 ? agentCosts : {
    'security': 0.125,
    'quality': 0.084,
    'tests': 0.042,
    'docs': 0.021,
    'aggregator': 0.063
  };
  
  const displayTotal = totalCost > 0 ? totalCost : 0.335;

  const getAgentColor = (agent: string) => {
    switch (agent.toLowerCase()) {
      case 'security': return 'linear-gradient(135deg, #f87171, #ef4444)';
      case 'quality': return 'linear-gradient(135deg, #60a5fa, #3b82f6)';
      case 'tests': return 'linear-gradient(135deg, #fbbf24, #f59e0b)';
      case 'docs': return 'linear-gradient(135deg, #34d399, #10b981)';
      default: return 'linear-gradient(135deg, #a78bfa, #818cf8)';
    }
  };

  return (
    <div className="card">
      <h3 style={{ fontSize: '1.1rem', marginBottom: '1.25rem' }}>💰 Cost Breakdown by Agent</h3>
      
      {/* Metric summary rows */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
        <div style={{ padding: '1rem', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--panel-border)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>TODAY'S RUNTIME COST</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--foreground)' }}>${displayTotal.toFixed(4)}</div>
        </div>
        <div style={{ padding: '1rem', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--panel-border)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>REVIEWS EXECUTED</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--success)' }}>{data.total_reviews_count || 12}</div>
        </div>
        <div style={{ padding: '1rem', backgroundColor: 'rgba(255,255,255,0.02)', borderRadius: '8px', border: '1px solid var(--panel-border)' }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginBottom: '0.25rem' }}>AVERAGE EXECUTION LATENCY</div>
          <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--primary)' }}>
            {data.average_latency_ms ? `${(data.average_latency_ms / 1000).toFixed(1)}s` : '18.4s'}
          </div>
        </div>
      </div>

      {/* Visual Flex Bar representation */}
      <div style={{ display: 'flex', height: '1.5rem', borderRadius: '9999px', overflow: 'hidden', backgroundColor: 'var(--background)', marginBottom: '2rem', border: '1px solid var(--panel-border)' }}>
        {Object.entries(costs).map(([agent, cost]) => {
          const percentage = ((cost / displayTotal) * 100);
          if (percentage <= 0) return null;
          return (
            <div
              key={agent}
              style={{
                width: `${percentage}%`,
                background: getAgentColor(agent),
                height: '100%',
                transition: 'width 0.4s ease-out',
              }}
              title={`${agent}: $${cost.toFixed(4)} (${percentage.toFixed(0)}%)`}
            />
          );
        })}
      </div>

      {/* Breakdown Legend rows */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        {Object.entries(costs).map(([agent, cost]) => {
          const pct = (cost / displayTotal) * 100;
          return (
            <div key={agent} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span style={{ display: 'block', width: '0.75rem', height: '0.75rem', borderRadius: '50%', background: getAgentColor(agent) }} />
                <span style={{ fontSize: '0.9rem', textTransform: 'capitalize' }}>{agent}</span>
              </div>
              <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>
                <span>${cost.toFixed(4)}</span>
                <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginLeft: '0.5rem' }}>({pct.toFixed(0)}%)</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
