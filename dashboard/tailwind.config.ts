import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#003366',
          80: '#1A4D80',
          60: '#336699',
          30: '#99BBDD',
          10: '#E0EAF4',
        },
        gold: {
          DEFAULT: '#C8982A',
          light: '#E8C46A',
        },
        dark: '#1C1C2E',
        mid: '#6B7280',
        light: '#F4F6F9',
        zone: {
          green: '#27B97C',
          'green-bg': '#E0F7EF',
          'green-text': '#0D5C3A',
          yellow: '#F07020',
          'yellow-bg': '#FEF0E6',
          'yellow-text': '#7A3800',
          red: '#E03448',
          'red-bg': '#FDEAEA',
          'red-text': '#7A1020',
        },
      },
      fontFamily: {
        display: ["'Fraunces'", 'Georgia', 'serif'],
        body: ["'Plus Jakarta Sans'", 'sans-serif'],
        mono: ['Courier New', 'monospace'],
      },
      fontSize: {
        label: ['10px', { letterSpacing: '3px', fontWeight: '500' }],
        eyebrow: ['9px', { letterSpacing: '4px', fontWeight: '500' }],
      },
      borderRadius: {
        card: '12px',
      },
      maxWidth: {
        content: '1200px',
        dashboard: '1300px',
      },
      boxShadow: {
        card: '0 1px 4px rgba(0, 51, 102, 0.08)',
        'card-md': '0 1px 6px rgba(0, 51, 102, 0.09)',
      },
    },
  },
  plugins: [],
};

export default config;
