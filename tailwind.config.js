/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html", // Jinja2テンプレートを含むHTMLファイルを指定
    // "./static/**/*.js",    // JavaScriptファイル内でTailwindクラスを動的に追加する場合
  ],
  theme: {
    extend: {},
  },
  plugins: [],
}

