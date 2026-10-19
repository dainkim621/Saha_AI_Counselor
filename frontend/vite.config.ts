import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],

  server: {
    host: "127.0.0.1", //일단 로컬 접근만 허용~~

    proxy: {
      "/ai-chat": backend,
      "/frequent-questions": backend,
      "/stt": backend,
      "/api": backend,

      // 관리자 API만 FastAPI로 전달
      "/admin": {
        target: backend,
        changeOrigin: true,

        bypass(req) {
          // 브라우저에서 관리자 페이지를 열 때는 React가 처리
          if (
            req.method === "GET" &&
            (req.url === "/admin" ||
              req.url?.startsWith("/admin/login") ||
              req.url?.startsWith("/admin/signup"))
          ) {
            return "/index.html";
          }
        },
      },
    },
  },
});