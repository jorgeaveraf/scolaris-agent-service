/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}", "../chat-widget/src/lib/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "rgb(var(--accent-primary) / <alpha-value>)",
          dark: "rgb(var(--accent-dark) / <alpha-value>)",
          light: "rgb(var(--accent-light) / <alpha-value>)",
        },
        slate: {
          25: "#F8FAFC",
        },
        ink: {
          DEFAULT: "#1E293B",
          muted: "#475569",
        },
        border: "#E2E8F0",
      },
      fontFamily: {
        sans: ["Inter", "Poppins", "ui-sans-serif", "system-ui"],
      },
      boxShadow: {
        card: "0 10px 25px -15px rgba(15, 23, 42, 0.25)",
      },
    },
  },
  plugins: [],
};
