/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: {
          950: "#ffffff",
          900: "#f4f4f5",
          800: "#e4e4e7",
          700: "#d4d4d8",
          600: "#a1a1aa",
          400: "#71717a",
          300: "#3f3f46",
          200: "#27272a",
          100: "#09090b",
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
      keyframes: {
        accordionOpen: {
          from: { height: "0px" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        accordionClose: {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0px" },
        },
      },
      animation: {
        accordionOpen: "accordionOpen 0.15s ease-in-out",
        accordionClose: "accordionClose 0.15s ease-in-out",
      },
    },
  },
  plugins: [],
};
