/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        background: "#0b0f17",
        surface: "#121824",
        "surface-elevated": "#1a2333",
        border: "#222f44",
        "border-light": "#2f4260",
        primary: {
          DEFAULT: "#2563eb",
          hover: "#1d4ed8",
          light: "#3b82f6",
        },
        flood: {
          permanent: "#0284c7", // Deep blue
          new: "#ef4444", // Critical red/orange
          receded: "#10b981", // Green
          uncertain: "#f59e0b", // Amber
        },
      },
    },
  },
  plugins: [],
};
