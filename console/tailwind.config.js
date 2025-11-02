/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#007BFF",
          dark: "#0056B3",
          light: "#0D6EFD",
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
