import type { Config } from "tailwindcss";

export default {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "var(--background)",
        foreground: "var(--foreground)",
        primary: {
          DEFAULT: "var(--colors-primary-DEFAULT)",
          50: "var(--colors-primary-50)",
          100: "var(--colors-primary-100)",
          200: "var(--colors-primary-200)",
          300: "var(--colors-primary-300)",
          400: "var(--colors-primary-400)",
          500: "var(--colors-primary-500)",
          600: "var(--colors-primary-600)",
          700: "var(--colors-primary-700)",
          800: "var(--colors-primary-800)",
          900: "var(--colors-primary-900)",
        },
        secondary: {
          DEFAULT: "var(--colors-secondary-DEFAULT)",
          50: "var(--colors-secondary-50)",
          100: "var(--colors-secondary-100)",
          200: "var(--colors-secondary-200)",
          300: "var(--colors-secondary-300)",
          400: "var(--colors-secondary-400)",
          500: "var(--colors-secondary-500)",
          600: "var(--colors-secondary-600)",
          700: "var(--colors-secondary-700)",
          800: "var(--colors-secondary-800)",
          900: "var(--colors-secondary-900)",
        },
        card: {
          DEFAULT: "var(--colors-surface-card)",
          border: "var(--colors-surface-card-border)",
        }
      },
    },
  },
  plugins: [],
} satisfies Config;
