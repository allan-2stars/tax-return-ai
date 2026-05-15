/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        ato: {
          yellow: "#fef9c3",
          "yellow-border": "#eab308",
          "yellow-text": "#713f12",
          blue: "#1d4ed8",
          green: "#15803d",
          red: "#b91c1c",
        },
      },
    },
  },
  plugins: [],
};
