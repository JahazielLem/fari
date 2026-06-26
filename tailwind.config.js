/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./webapp/templates/**/*.html"],
  darkMode: "class",
  safelist: [
    "bg-latte-blue/10",
    "dark:bg-mocha-blue/20",
    "dark:hover:bg-mocha-surface0",
  ],
  theme: {
    extend: {
      colors: {
        "latte-base": "#eff1f5",
        "latte-mantle": "#e6e9ef",
        "latte-crust": "#dce0e8",
        "latte-text": "#4c4f69",
        "latte-subtext0": "#6c6f85",
        "latte-overlay0": "#9ca0b0",
        "latte-surface0": "#ccd0da",
        "latte-surface1": "#bcc0cc",
        "latte-blue": "#1e66f5",
        "latte-sky": "#04a5e5",
        "latte-green": "#40a02b",
        "latte-yellow": "#df8e1d",
        "latte-red": "#d20f39",
        "mocha-base": "#1e1e2e",
        "mocha-mantle": "#181825",
        "mocha-crust": "#11111b",
        "mocha-text": "#cdd6f4",
        "mocha-subtext0": "#a6adc8",
        "mocha-overlay0": "#6c7086",
        "mocha-surface0": "#313244",
        "mocha-surface1": "#45475a",
        "mocha-blue": "#89b4fa",
        "mocha-sky": "#89dceb",
        "mocha-green": "#a6e3a1",
        "mocha-yellow": "#f9e2af",
        "mocha-red": "#f38ba8"
      },
      boxShadow: {
        soft: "0 18px 50px rgba(30, 30, 46, .10)"
      }
    }
  },
  plugins: []
};
