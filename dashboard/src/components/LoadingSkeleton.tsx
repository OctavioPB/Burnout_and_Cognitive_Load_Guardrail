/** Shimmer loading skeleton — used for cards and chart placeholders. */

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  style?: React.CSSProperties;
}

export function Skeleton({ width = '100%', height = 16, borderRadius = 6, style }: SkeletonProps) {
  return (
    <div
      aria-hidden="true"
      style={{
        width,
        height,
        borderRadius,
        background: 'linear-gradient(90deg, #e8edf4 25%, #f4f6f9 50%, #e8edf4 75%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.4s ease-in-out infinite',
        ...style,
      }}
    />
  );
}

export function CardSkeleton() {
  return (
    <div
      aria-busy="true"
      aria-label="Loading..."
      style={{
        backgroundColor: 'var(--white)',
        borderRadius: 12,
        boxShadow: '0 1px 4px rgba(0,51,102,0.08)',
        padding: 24,
        display: 'flex',
        flexDirection: 'column',
        gap: 12,
      }}
    >
      <Skeleton height={14} width="40%" />
      <Skeleton height={32} width="60%" />
      <Skeleton height={12} width="80%" />
      <Skeleton height={12} width="55%" />
    </div>
  );
}

export function ChartSkeleton({ height = 280 }: { height?: number }) {
  return (
    <div
      aria-busy="true"
      aria-label="Loading chart..."
      style={{
        backgroundColor: 'var(--white)',
        borderRadius: 12,
        boxShadow: '0 1px 4px rgba(0,51,102,0.08)',
        padding: 24,
      }}
    >
      <Skeleton height={14} width="35%" style={{ marginBottom: 8 }} />
      <Skeleton height={10} width="55%" style={{ marginBottom: 24 }} />
      <Skeleton height={height} borderRadius={8} />
    </div>
  );
}

// Inject keyframe animation into document head once
if (typeof document !== 'undefined' && !document.getElementById('skeleton-keyframes')) {
  const style = document.createElement('style');
  style.id = 'skeleton-keyframes';
  style.textContent = `
    @keyframes shimmer {
      0%   { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `;
  document.head.appendChild(style);
}
