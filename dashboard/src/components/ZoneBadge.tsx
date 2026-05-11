/** Reusable Green / Yellow / Red resilience zone badge. */

import type { ResilienceZone } from '../types/domain';

const ZONE_CONFIG: Record<ResilienceZone, { bg: string; text: string; dot: string; label: string }> = {
  green:  { bg: '#E0F7EF', text: '#0D5C3A', dot: '#27B97C', label: 'Healthy'   },
  yellow: { bg: '#FEF0E6', text: '#7A3800', dot: '#F07020', label: 'Monitor'   },
  red:    { bg: '#FDEAEA', text: '#7A1020', dot: '#E03448', label: 'Intervene' },
};

interface ZoneBadgeProps {
  zone: ResilienceZone;
  /** Show a larger, more prominent badge */
  size?: 'sm' | 'md';
  /** Override the displayed label */
  label?: string;
}

export function ZoneBadge({ zone, size = 'sm', label }: ZoneBadgeProps) {
  const { bg, text, dot, label: defaultLabel } = ZONE_CONFIG[zone];
  const displayLabel = label ?? defaultLabel;
  const fontSize = size === 'md' ? 11 : 10;
  const dotSize = size === 'md' ? 7 : 6;
  const padding = size === 'md' ? '5px 14px' : '4px 12px';

  return (
    <span
      role="status"
      aria-label={`Zone: ${displayLabel}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: 6,
        backgroundColor: bg,
        color: text,
        borderRadius: 20,
        padding,
        fontSize,
        fontFamily: 'var(--fb)',
        fontWeight: 500,
        letterSpacing: '0.5px',
        whiteSpace: 'nowrap',
      }}
    >
      <span
        aria-hidden="true"
        style={{
          width: dotSize,
          height: dotSize,
          borderRadius: '50%',
          backgroundColor: dot,
          flexShrink: 0,
        }}
      />
      {displayLabel}
    </span>
  );
}
