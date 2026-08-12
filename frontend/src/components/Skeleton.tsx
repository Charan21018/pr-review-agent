import React from 'react';

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  radius?: string;
  style?: React.CSSProperties;
}

export const Skeleton: React.FC<SkeletonProps> = ({ width = '100%', height = '1rem', radius, style }) => (
  <div className="skeleton" style={{ width, height, borderRadius: radius, ...style }} />
);

export const PageSkeleton: React.FC<{ label: string }> = ({ label }) => (
  <div className="main-container">
    <div style={{ marginBottom: '2rem' }}>
      <Skeleton width={280} height={32} radius="8px" style={{ marginBottom: '0.6rem' }} />
      <Skeleton width={420} height={16} radius="6px" />
    </div>
    <div className="stats-grid">
      {[0, 1, 2, 3].map((i) => (
        <div key={i} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
          <Skeleton width={38} height={38} radius="10px" />
          <Skeleton width="70%" height={28} radius="6px" />
          <Skeleton width="50%" height={12} radius="4px" />
        </div>
      ))}
    </div>
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '30vh', color: 'var(--text-muted)', fontSize: '0.9rem' }}>
      {label}
    </div>
  </div>
);
