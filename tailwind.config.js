/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: ["class"],
  content: [
    "./app/**/*.{ts,tsx,js,jsx}",
    "./components/**/*.{ts,tsx,js,jsx}",
    "./pages/**/*.{ts,tsx,js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(214, 30%, 91%)",
        background: "#f8fafc",
        card: "#ffffff",
        primary: {
          DEFAULT: "#2563eb",
          foreground: "#ffffff"
        },
        muted: "#f1f5f9",
        ring: "#93c5fd"
      },
      boxShadow: {
        card: "0 1px 2px rgba(0,0,0,0.04), 0 4px 12px rgba(0,0,0,0.06)"
      }
    },
  },
  plugins: [require('@tailwindcss/forms')],
}


