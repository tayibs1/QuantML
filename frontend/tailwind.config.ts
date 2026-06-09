import type { Config } from "tailwindcss";

const config: Config = {
  darkMode: "class",
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)", "system-ui", "sans-serif"],
        mono: ["var(--font-mono)", "ui-monospace", "monospace"],
      },
      colors: {
        ink: {
          950: "#04060c",
          900: "#070a12",
          850: "#0a0e1a",
          800: "#0e1322",
          750: "#131a2c",
          700: "#1a2236",
        },
        brand: {
          DEFAULT: "#2dd4bf",
          50: "#effdfa",
          100: "#cbfdf2",
          200: "#97f9e6",
          300: "#5deeda",
          400: "#2dd4bf",
          500: "#14b8a6",
          600: "#0d9488",
          glow: "#2dd4bf",
        },
        violet: {
          DEFAULT: "#8b5cf6",
          glow: "#a78bfa",
        },
        bull: {
          DEFAULT: "#22c55e",
          soft: "#34d399",
        },
        bear: {
          DEFAULT: "#f43f5e",
          soft: "#fb7185",
        },
        hold: {
          DEFAULT: "#f59e0b",
          soft: "#fbbf24",
        },
      },
      borderRadius: {
        xl: "0.875rem",
        "2xl": "1.125rem",
        "3xl": "1.5rem",
      },
      boxShadow: {
        glow: "0 0 0 1px rgba(45,212,191,0.18), 0 0 28px -6px rgba(45,212,191,0.35)",
        "glow-violet":
          "0 0 0 1px rgba(139,92,246,0.18), 0 0 28px -6px rgba(139,92,246,0.35)",
        panel:
          "0 1px 0 0 rgba(255,255,255,0.04) inset, 0 24px 60px -28px rgba(0,0,0,0.9)",
        "panel-lg":
          "0 1px 0 0 rgba(255,255,255,0.05) inset, 0 40px 90px -40px rgba(0,0,0,0.95)",
      },
      keyframes: {
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-10px)" },
        },
        "float-slow": {
          "0%, 100%": { transform: "translateY(0px)" },
          "50%": { transform: "translateY(-16px)" },
        },
        shimmer: {
          "0%": { transform: "translateX(-100%)" },
          "100%": { transform: "translateX(100%)" },
        },
        "spin-slow": {
          to: { transform: "rotate(360deg)" },
        },
        "pulse-glow": {
          "0%, 100%": { opacity: "0.5" },
          "50%": { opacity: "1" },
        },
        marquee: {
          "0%": { transform: "translateX(0)" },
          "100%": { transform: "translateX(-50%)" },
        },
        "gradient-x": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        scan: {
          "0%": { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        "border-flow": {
          "0%, 100%": { backgroundPosition: "0% 50%" },
          "50%": { backgroundPosition: "100% 50%" },
        },
        blink: {
          "0%, 49%": { opacity: "1" },
          "50%, 100%": { opacity: "0" },
        },
      },
      animation: {
        "fade-up": "fade-up 0.6s cubic-bezier(0.21,0.6,0.35,1) both",
        float: "float 6s ease-in-out infinite",
        "float-slow": "float-slow 9s ease-in-out infinite",
        shimmer: "shimmer 2.5s ease-in-out infinite",
        "spin-slow": "spin-slow 14s linear infinite",
        "pulse-glow": "pulse-glow 3s ease-in-out infinite",
        marquee: "marquee 40s linear infinite",
        "gradient-x": "gradient-x 6s ease infinite",
        scan: "scan 6s linear infinite",
        "border-flow": "border-flow 4s ease infinite",
        blink: "blink 1.2s step-end infinite",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(ellipse 80% 60% at 50% -10%, rgba(45,212,191,0.10), transparent 60%)",
      },
    },
  },
  plugins: [],
};

export default config;
