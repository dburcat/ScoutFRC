/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        serif: ['"Instrument Serif"', 'Georgia', 'serif'],
        sans:  ['"DM Sans"', 'system-ui', 'sans-serif'],
      },
      colors: {
        sand: {
          50:  '#faf9f6',
          100: '#f2efe8',
          200: '#e8e4db',
          300: '#d8d4c8',
          400: '#b8b4a8',
          500: '#8a8880',
          600: '#5c5a54',
          900: '#1a1814',
        },
        accent: {
          DEFAULT: '#2a5c3f',
          light:   '#eaf3de',
        },
      },
    },
  },
  plugins: [],
};