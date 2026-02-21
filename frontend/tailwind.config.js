/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // GCash brand — primary blue (#007DFE)
        primary: {
          50:  '#EBF5FF',
          100: '#D6EBFF',
          200: '#ADD6FF',
          300: '#85C2FF',
          400: '#5CADFF',
          500: '#007DFE',
          600: '#0064CB',
          700: '#004B98',
          800: '#003265',
          900: '#001932',
        },
        // Dashboard stat card palette (blue-shifted complementary)
        stat: {
          blue:    { light: '#EBF5FF', DEFAULT: '#007DFE', dark: '#0064CB' },
          teal:    { light: '#E6FAFB', DEFAULT: '#0891B2', dark: '#0E7490' },
          violet:  { light: '#EDE9FE', DEFAULT: '#7C3AED', dark: '#6D28D9' },
          emerald: { light: '#ECFDF5', DEFAULT: '#059669', dark: '#047857' },
        },
        // Page & card surfaces
        surface: {
          DEFAULT: '#F7F8FA',
          alt:     '#F0F4F8',
        },
        // Confidence level colors
        confidence: {
          high:   '#10b981',
          medium: '#f59e0b',
          low:    '#ef4444',
        },
        // Severity colors
        severity: {
          high:   '#dc2626',
          medium: '#d97706',
          low:    '#059669',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'monospace'],
      },
      boxShadow: {
        card: '0 2px 8px rgba(0, 0, 0, 0.08)',
      },
      borderRadius: {
        card: '0.75rem',
      },
    },
  },
  plugins: [],
}
