/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Base tokens referenced by index.css (@apply border-border, etc.).
        border: '#e2e8f0',
        input: '#e2e8f0',
        ring: '#0a66c2',
        background: '#ffffff',
        foreground: '#0f172a',
        linkedin: {
          50: '#e7f3ff',
          100: '#d0e7ff',
          200: '#a8d4ff',
          300: '#74baff',
          400: '#3d95ff',
          500: '#0a66c2',
          600: '#004182',
          700: '#002e5f',
          800: '#001d3d',
          900: '#000f1f',
        },
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'spin-slow': 'spin 3s linear infinite',
      },
    },
  },
  plugins: [],
}
