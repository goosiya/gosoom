/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
    "../../packages/ui/src/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#1360F5",
          foreground: "#FFFFFF",
          pressed: "#0F4FCC",
        },
        border: "#E2E8F0",
        muted: {
          DEFAULT: "#F8FAFC",
          foreground: "#64748B",
        },
        destructive: {
          DEFAULT: "#DC2626",
          foreground: "#FFFFFF",
        },
      },
    },
  },
  plugins: [],
};
