import { BrowserRouter, Routes, Route } from "react-router-dom";

import App from "./App";
import AdminDashboard from "./pages/AdminDashboard";
import AdminLogin from "./pages/AdminLogin";

/*
 * 사용자용 챗봇과 관리자 페이지의 URL 경로를 관리
 */
function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>
        {/* 시민용 챗봇 */}
        <Route path="/" element={<App />} />

        {/* 관리자 로그인 */}
        <Route
          path="/admin/login"
          element={<AdminLogin />}
        />

        {/* 관리자 대시보드 */}
        <Route
          path="/admin"
          element={<AdminDashboard />}
        />
      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;