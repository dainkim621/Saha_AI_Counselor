
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";

import "../../styles/AdminDashboard.css";

// 관리자 페이지 공통 레이아웃
function AdminLayout() {
  const navigate = useNavigate();

  // 사이드바 접기 및 펼치기 상태
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);

  // 사이드바 상태 전환
  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };

  // 관리자 로그아웃 처리
  const handleLogout = async () => {
    try {
      const response = await fetch(
        "http://localhost:8000/admin/logout",
        {
          method: "POST",
          credentials: "include",
        }
      );

      if (response.ok) {
        navigate("/admin/login", { replace: true });
      } else {
        console.error("로그아웃 실패:", response.status);
      }
    } catch (error) {
      console.error("로그아웃 요청 중 오류:", error);
    }
  };

  return (
    <div className="admin-layout">

      {/* 왼쪽 관리자 사이드바 */}
      <aside
        className={`admin-sidebar ${
          isSidebarOpen ? "expanded" : "collapsed"
        }`}
      >

        {/* 관리자 시스템 브랜드 */}
        <div className="admin-sidebar-brand">

          {isSidebarOpen && (
            <div className="admin-sidebar-brand-text">
              <div className="admin-sidebar-logo">
                사하구 AI 민원 상담사
              </div>
              <span>ADMIN SYSTEM</span>
            </div>
          )}

          {/* 사이드바 접기 및 펼치기 */}
          <button
            type="button"
            className="admin-sidebar-toggle"
            onClick={toggleSidebar}
            aria-label={
              isSidebarOpen
                ? "사이드바 접기"
                : "사이드바 펼치기"
            }
            aria-expanded={isSidebarOpen}
          >
            ☰
          </button>
        </div>

        {/* 관리자 메뉴 */}
        <nav
          className="admin-sidebar-nav"
          aria-label="관리자 메뉴"
        >

          {/* 질문 분석 대시보드 */}
          <NavLink
            to="/admin"
            end
            className={({ isActive }) =>
              `admin-sidebar-menu ${
                isActive ? "active" : ""
              }`
            }
            title="질문 분석 대시보드"
          >
            <span className="admin-sidebar-menu-icon">
              ▦
            </span>

            {isSidebarOpen && (
              <span>질문 분석 대시보드</span>
            )}
          </NavLink>

          {/* 관리자 관리 */}
          <NavLink
            to="/admin/management"
            className={({ isActive }) =>
              `admin-sidebar-menu ${
                isActive ? "active" : ""
              }`
            }
            title="관리자 관리"
          >
            <span className="admin-sidebar-menu-icon">
              ♙
            </span>

            {isSidebarOpen && (
              <span>관리자 관리</span>
            )}
          </NavLink>

        </nav>

        {/* 로그아웃 영역 */}
        <div className="admin-sidebar-footer">
          <button
            type="button"
            className="admin-sidebar-logout"
            onClick={handleLogout}
            title="로그아웃"
            aria-label="로그아웃"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
              <polyline points="16 17 21 12 16 7" />
              <line x1="21" y1="12" x2="9" y2="12" />
            </svg>

            {isSidebarOpen && (
              <span>로그아웃</span>
            )}
          </button>
        </div>

      </aside>

      {/* 오른쪽 관리자 페이지 공통 영역 */}
      <div className="admin-main-content">
        <Outlet />
      </div>

    </div>
  );
}

export default AdminLayout;
