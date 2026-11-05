/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        bg: "#0b0d12",
        card: "#12151d",
        border: "#292d39",
        accent: "#a78bfa",
        primary: {
          from: "#d4d4d8",
          to: "#a1a1aa",
        },
        success: "#86efac",
        error: "#fca5a5",
        warning: "#fcd34d",
        muted: "#a1a1aa",
      },
      fontFamily: {
        sans: ["IBM Plex Sans", "Segoe UI", "sans-serif"],
        mono: ["IBM Plex Mono", "Consolas", "monospace"],
      },
      borderRadius: {
        card: "8px",
      },
    },
  },
  plugins: [],
};
