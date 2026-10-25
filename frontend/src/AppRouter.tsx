
import {
  BrowserRouter,
  Routes,
  Route,
} from "react-router-dom";

import App from "./App";

import AdminDashboard from "./pages/AdminDashboard";
import AdminLogin from "./pages/AdminLogin";
import AdminSignup from "./pages/AdminSignup";
import AdminManagement from "./pages/AdminManagement";

import AdminLayout from "./components/admin/AdminLayout";
import ProtectedAdminRoute from "./components/admin/ProtectedAdminRoute";

// 사용자용 챗봇과 관리자 페이지 URL 관리
function AppRouter() {
  return (
    <BrowserRouter>
      <Routes>

        {/* 시민용 챗봇 */}
        <Route
          path="/"
          element={<App />}
        />

        {/* 관리자 로그인 */}
        <Route
          path="/admin/login"
          element={<AdminLogin />}
        />

        {/* 관리자 회원가입 */}
        <Route
          path="/admin/signup"
          element={<AdminSignup />}
        />

        {/* 관리자 공통 레이아웃 */}
        <Route
          path="/admin"
          element={
            <ProtectedAdminRoute>
              <AdminLayout />
            </ProtectedAdminRoute>
          }
        >

          {/* 질문 분석 대시보드 */}
          <Route
            index
            element={<AdminDashboard />}
          />

          {/* 관리자 관리 */}
          <Route
            path="management"
            element={<AdminManagement />}
          />

        </Route>

      </Routes>
    </BrowserRouter>
  );
}

export default AppRouter;
