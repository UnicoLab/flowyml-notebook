/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  darkMode: 'class',
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Menlo', 'Monaco', 'monospace'],
      },
      colors: {
        navy: {
          900: '#0f172a', 800: '#1e293b', 700: '#334155',
          600: '#475569', 500: '#64748b',
        },
        accent: {
          DEFAULT: '#3b82f6', light: '#60a5fa', dark: '#2563eb',
          glow: 'rgba(59, 130, 246, 0.15)',
        },
        cell: {
          success: '#10b981', error: '#ef4444', stale: '#f59e0b',
          running: '#8b5cf6',
        },
      },
      animation: {
        'pulse-glow': 'pulse-glow 2s infinite',
        'slide-in': 'slide-in 0.2s ease-out',
      },
      keyframes: {
        'pulse-glow': {
          '0%, 100%': { boxShadow: '0 0 0 0 rgba(59, 130, 246, 0.2)' },
          '50%': { boxShadow: '0 0 20px 4px rgba(59, 130, 246, 0.15)' },
        },
        'slide-in': {
          from: { transform: 'translateY(-8px)', opacity: '0' },
          to: { transform: 'translateY(0)', opacity: '1' },
        },
      },
    },
  },
  plugins: [],
};
