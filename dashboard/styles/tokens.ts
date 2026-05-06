/**
 * Design tokens sourced from BRAND.md.
 * All visual decisions (colors, typography, spacing) must trace back to this file.
 * Import these values into components — never hardcode hex codes or font strings.
 */

// ─── Color palette ────────────────────────────────────────────────────────────
export const colors = {
  primary:    '#003366',
  primary80:  '#1A4D80',
  primary60:  '#336699',
  primary30:  '#99BBDD',
  primary10:  '#E0EAF4',
  gold:       '#C8982A',
  goldLight:  '#E8C46A',
  dark:       '#1C1C2E',
  mid:        '#6B7280',
  light:      '#F4F6F9',
  white:      '#FFFFFF',
} as const;

// ─── Resilience zone semantic colors ──────────────────────────────────────────
export const zoneColors = {
  green:  { base: '#27B97C', bg: '#E0F7EF', text: '#0D5C3A' },
  yellow: { base: '#F07020', bg: '#FEF0E6', text: '#7A3800' },
  red:    { base: '#E03448', bg: '#FDEAEA', text: '#7A1020' },
  purple: { base: '#7C4DBD', bg: '#F0EBF9', text: '#3D1F70' },
  blue:   { base: '#003366', bg: '#E0EAF4', text: '#001F4D' },
} as const;

export type ZoneColor = keyof typeof zoneColors;

// ─── Resilience zones ─────────────────────────────────────────────────────────
export const resilienceZones = {
  green:  { label: 'Healthy',   afsMin: 0,  afsMax: 39,  ...zoneColors.green  },
  yellow: { label: 'Monitor',   afsMin: 40, afsMax: 69,  ...zoneColors.yellow },
  red:    { label: 'Intervene', afsMin: 70, afsMax: 100, ...zoneColors.red    },
} as const;

export type ResilienceZone = keyof typeof resilienceZones;

export function getResilienceZone(afs: number): ResilienceZone {
  if (afs <= 39) return 'green';
  if (afs <= 69) return 'yellow';
  return 'red';
}

// ─── Data visualization series (use in order for multi-series charts) ─────────
export const chartColors = [
  '#003366',  // corporate blue
  '#27B97C',  // green
  '#7C4DBD',  // purple
  '#F07020',  // orange
  '#E05080',  // pink
] as const;

// ─── Typography ───────────────────────────────────────────────────────────────
export const fonts = {
  display: "'Fraunces', Georgia, serif",
  body:    "'Plus Jakarta Sans', sans-serif",
  mono:    'Courier New, monospace',
} as const;

export const typography = {
  heroTitle:  { fontFamily: fonts.display, fontSize: '48px', fontWeight: 300 },
  h1:         { fontFamily: fonts.display, fontSize: '32px', fontWeight: 400 },
  h2:         { fontFamily: fonts.display, fontSize: '22px', fontWeight: 300 },
  h3:         { fontFamily: fonts.body,    fontSize: '16px', fontWeight: 600 },
  body:       { fontFamily: fonts.body,    fontSize: '15px', fontWeight: 400, lineHeight: 1.7 },
  caption:    { fontFamily: fonts.body,    fontSize: '12px', fontWeight: 400, color: colors.mid },
  label:      { fontFamily: fonts.body,    fontSize: '10px', fontWeight: 500, textTransform: 'uppercase' as const, letterSpacing: '3px' },
  eyebrow:    { fontFamily: fonts.body,    fontSize: '9px',  fontWeight: 500, textTransform: 'uppercase' as const, letterSpacing: '4px' },
  code:       { fontFamily: fonts.mono,    fontSize: '13px', fontWeight: 400 },
} as const;

// ─── Spacing ──────────────────────────────────────────────────────────────────
export const spacing = {
  componentGap: '16px',
  sectionGap:   '24px',
  cardPadding:  '28px',
  sectionPadding: { desktop: '96px 48px', mobile: '64px 24px' },
} as const;

// ─── Component tokens ─────────────────────────────────────────────────────────
export const card = {
  background:   colors.white,
  borderRadius: '12px',
  boxShadow:    '0 1px 4px rgba(0, 51, 102, 0.08)',
  padding:      spacing.cardPadding,
} as const;

export const nav = {
  background:    'rgba(0, 51, 102, 0.97)',
  backdropFilter: 'blur(12px)',
  height:        '52px',
  borderBottom:  '1px solid rgba(255, 255, 255, 0.08)',
  padding:       '0 40px',
} as const;

export const accentBar = {
  height:     '3px',
  background: colors.gold,
} as const;

export const sectionDivider = {
  height:     '1px',
  background: colors.primary10,
} as const;

// ─── Layout ───────────────────────────────────────────────────────────────────
export const layout = {
  maxWidthContent:   '1200px',
  maxWidthDashboard: '1300px',
  pageBackground:    colors.light,
} as const;
