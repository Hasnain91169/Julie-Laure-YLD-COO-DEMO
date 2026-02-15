import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ink: "#122230",
        surface: "#f6f8f9",
        accent: "#0f766e",
        coral: "#ea580c",
      },
      fontFamily: {
        sans: ["var(--font-manrope)", "Segoe UI", "sans-serif"],
      },
      boxShadow: {
        card: "0 10px 30px rgba(16, 33, 50, 0.08)",
      },
    },
  },
  plugins: [],
};

export default config;
