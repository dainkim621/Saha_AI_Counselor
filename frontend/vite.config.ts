import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

export default defineConfig({
  plugins: [react(), tailwindcss()],

  server: {
    host: "0.0.0.0",
    proxy: {
      "/ai-chat": "http://127.0.0.1:8000",
      "/frequent-questions": "http://127.0.0.1:8000",
      "/stt": "http://127.0.0.1:8000",
      "/api": "http://127.0.0.1:8000",
      "/admin": "http://127.0.0.1:8000",
    },
  },
});