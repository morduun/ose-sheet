/** @type {import('tailwindcss').Config} */
export default {
  content: ['./src/**/*.{html,js,svelte,ts}'],
  theme: {
    extend: {
      colors: {
        parchment: {
          50: 'rgb(var(--color-parchment-50) / <alpha-value>)',
          100: 'rgb(var(--color-parchment-100) / <alpha-value>)',
          200: 'rgb(var(--color-parchment-200) / <alpha-value>)',
          300: 'rgb(var(--color-parchment-300) / <alpha-value>)',
          DEFAULT: 'rgb(var(--color-parchment) / <alpha-value>)',
        },
        ink: {
          DEFAULT: 'rgb(var(--color-ink) / <alpha-value>)',
          light: 'rgb(var(--color-ink-light) / <alpha-value>)',
          faint: 'rgb(var(--color-ink-faint) / <alpha-value>)',
        },
      },
      fontFamily: {
        serif: ['var(--font-serif)'],
        sans: ['var(--font-sans)'],
      },
    },
  },
  plugins: [],
};
