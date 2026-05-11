/** Consistent footer per BRAND.md — primary bg, 9px uppercase, flex space-between. */

export function Footer() {
  const date = new Date()
    .toLocaleDateString('en-US', { year: 'numeric', month: 'long' })
    .toUpperCase();

  return (
    <footer
      style={{
        backgroundColor: 'var(--primary)',
        padding: '20px 48px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontFamily: 'var(--fb)',
        fontSize: 9,
        letterSpacing: '3px',
        textTransform: 'uppercase',
        color: 'rgba(255,255,255,0.4)',
      }}
    >
      <span>OPB · Octavio Pérez Bravo · Burnout Guardrail</span>
      <span>{date}</span>
    </footer>
  );
}
