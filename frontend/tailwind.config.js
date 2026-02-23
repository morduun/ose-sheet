/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        parchment: {
          50: '#fdf8ed',
          100: '#f9efd6',
          200: '#f4e0b0',
          300: '#ecc878',
          DEFAULT: '#f4e8c1',
        },
        ink: {
          DEFAULT: '#2c1810',
          light: '#5c3d2e',
          faint: '#8b6347',
        },
      },
      fontFamily: {
        serif: ['"IM Fell English"', 'Georgia', 'serif'],
        sans: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
};
