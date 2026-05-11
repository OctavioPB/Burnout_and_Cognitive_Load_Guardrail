/** KPI stat card — left gold accent bar variant (dashboard layout per BRAND.md). */

interface KpiCardProps {
  value: string | number;
  label: string;
  sub?: string;
}

export function KpiCard({ value, label, sub }: KpiCardProps) {
  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'stretch',
        gap: 16,
        backgroundColor: 'var(--white)',
        borderRadius: 12,
        boxShadow: '0 1px 4px rgba(0,51,102,0.08)',
        overflow: 'hidden',
      }}
    >
      {/* Left accent bar */}
      <div style={{ width: 3, flexShrink: 0, backgroundColor: 'var(--gold)' }} />

      {/* Body */}
      <div style={{ padding: '20px 20px 20px 4px' }}>
        <div
          style={{
            fontFamily: 'var(--fd)',
            fontSize: 32,
            fontWeight: 300,
            color: 'var(--dark)',
            lineHeight: 1,
            marginBottom: 6,
          }}
        >
          {value}
        </div>
        <div
          style={{
            fontFamily: 'var(--fb)',
            fontSize: 10,
            fontWeight: 500,
            textTransform: 'uppercase',
            letterSpacing: '3px',
            color: 'var(--mid)',
          }}
        >
          {label}
        </div>
        {sub && (
          <div
            style={{
              fontFamily: 'var(--fb)',
              fontSize: 11,
              color: 'var(--mid)',
              marginTop: 4,
            }}
          >
            {sub}
          </div>
        )}
      </div>
    </div>
  );
}
