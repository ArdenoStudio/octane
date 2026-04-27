/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#0a0a0a",
          900: "#111113",
          800: "#1a1a1d",
          700: "#26262b",
          600: "#3f3f46",
          400: "#a1a1aa",
          300: "#d4d4d8",
          200: "#e4e4e7",
        },
        accent: {
          DEFAULT: "#f59e0b",
          dark: "#b45309",
        },
      },
      fontFamily: {
        sans: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        display: ["Inter", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: ["JetBrains Mono", "ui-monospace", "monospace"],
      },
      letterSpacing: {
        tightest: "-0.04em",
      },
    },
  },
  plugins: [],
};
