
 // 관리자 페이지에서 사용할 CSS 불러오기
import "../styles/AdminDashboard.css";
import { useNavigate } from "react-router-dom";
import { useState, useEffect } from "react";

import SummaryCards from "../components/admin/SummaryCards";
import FailedQuestions from "../components/admin/FailedQuestions";
import LanguageStats from "../components/admin/LanguageStats";
import HourlyUsage from "../components/admin/HourlyUsage";
import PopularQuestions from "../components/admin/PopularQuestions";
import MissingDocumentAreas from "../components/admin/MissingDocumentAreas";
const BACKEND_URL = "http://localhost:8000";
import {
  //dashboardSummaryMock, 이제 안씀
  failedQuestionsMock,
  languageStatsMock,
  hourlyUsageMock,
  popularQuestionsMock,
  missingDocumentAreasMock,
} from "../mocks/adminDashboardMock";

// 관리자 질문 분석 대시보드 화면
function AdminDashboard() {
  // 로그아웃 후 로그인 페이지로 이동하기 위해 사용
  const navigate = useNavigate();

  // 사이드바 접기 및 펼치기 상태
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  
  // 사이드바 상태 전환
  const toggleSidebar = () => {
    setIsSidebarOpen((prev) => !prev);
  };
  
  // 🌟 SummaryCards에 띄울 실제 데이터를 담을 상태(State) 선언
  const [summaryData, setSummaryData] = useState({
    totalQuestions: 0,
    failedQuestionCount: 0,
    topLanguage: "로딩 중...",
    peakHour: "로딩 중...",
  });

  // 🌟 백엔드에서 요약 통계 데이터를 가져오는 useEffect
  useEffect(() => {
    const fetchSummaryData = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/admin/dashboard/summary`, {
          credentials: "include", // 쿠키나 인증 정보를 함께 보낼 때 필요
        });

        if (response.ok) {
          const data = await response.json();
          setSummaryData({
            totalQuestions: data.totalQuestions,
            failedQuestionCount: data.failedQuestionCount,
            topLanguage: data.topLanguage,
            peakHour: data.peakHour,
          });
        }
      } catch (error) {
        console.error("대시보드 통계 데이터를 불러오는 중 오류 발생:", error);
      }
    };

    fetchSummaryData();
  }, []);
  
  // 관리자 로그아웃 처리
  const handleLogout = async () => {
    try {
      const response = await fetch(
        "http://localhost:8000/admin/logout",
        {
          method: "POST",

          // HttpOnly 관리자 세션 쿠키를 서버에 함께 전송
          credentials: "include",
        }
      );

      // 로그아웃에 성공하면 관리자 로그인 페이지로 이동
      if (response.ok) {
        navigate("/admin/login", { replace: true });
      }
    } catch (error) {
      console.error("로그아웃 요청 중 오류:", error);
    }
  };

  return (
    // 관리자 페이지 전체 레이아웃
    <div className="admin-layout">

      {/* 왼쪽 관리자 사이드바 */}
      <aside
        className={`admin-sidebar ${isSidebarOpen ? "expanded" : "collapsed"}`}
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
          
          {/* 사이드바 접기 및 펼치기 버튼 */}
          <button
            type="button"
            className="admin-sidebar-toggle"
            onClick={toggleSidebar}
            aria-label={isSidebarOpen ? "사이드바 접기" : "사이드바 펼치기"}
            aria-expanded={isSidebarOpen}
          >
            {isSidebarOpen ? "☰" : "☰"}
          </button>

        </div>

        {/* 사이드바 메뉴 */}
        <nav className="admin-sidebar-nav" aria-label="관리자 메뉴">

          {/* 현재 활성화된 질문 분석 메뉴 */}
          <div
            className="admin-sidebar-menu active"
            aria-current="page"
            title="질문 분석 대시보드"
          >
            <span className="admin-sidebar-menu-icon">▦</span>

            {isSidebarOpen && (
              <span>질문 분석 대시보드</span>
            )}
          </div>

          {/* 추후 구현할 관리자 관리 메뉴 */}
          <div
            className="admin-sidebar-menu disabled"
            title="관리자 관리 (추후 구현 예정)"
          >
            <span className="admin-sidebar-menu-icon">♙</span>

            {isSidebarOpen && (
              <>
                <span>관리자 관리</span>
                <span className="admin-sidebar-coming-soon">예정</span>
              </>
            )}
          </div>

        </nav>

        {/* 사이드바 로그아웃 */}
        <div className="admin-sidebar-footer">
          <button
            type="button"
            className="admin-sidebar-logout"
            onClick={handleLogout}
            title="로그아웃"
            aria-label="로그아웃"
          >
            {/* 로그아웃 아이콘 */}
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

            {isSidebarOpen && <span>로그아웃</span>}
          </button>
        </div>

      </aside>

      {/* 오른쪽 관리자 메인 화면 */}
      <div className="admin-main-content">

        <main className="admin-dashboard">

          {/* 관리자 대시보드 상단 헤더 */}
          <header className="admin-dashboard-header">
      
            {/* 관리자 시스템 브랜드 영역 */}
            <div className="admin-dashboard-brand">
              사하구 AI 민원 상담사
              <span>관리자 시스템</span>
            </div>
        
            {/* 제목 및 로그아웃 버튼 영역 */}
            <div className="admin-dashboard-header-row">
          
              {/* 페이지 제목 및 설명 */}
              <div className="admin-dashboard-title">
                <h1>관리자 질문 분석 대시보드</h1>
                <p>사용자 질문 통계와 답변 품질을 관리합니다.</p>
              </div>

            </div>
          </header>

          {/* 카드들을 배치하는 영역 */}
          <section className="dashboard-grid">
            <SummaryCards
              totalQuestions={summaryData.totalQuestions ?? 0}
              failedQuestionCount={summaryData.failedQuestionCount ?? 0}
              topLanguage={summaryData.topLanguage || "데이터 없음"}
              peakHour={summaryData.peakHour || "데이터 없음"}
            />

            <FailedQuestions questions={failedQuestionsMock} />
            <LanguageStats stats={languageStatsMock} />
            <HourlyUsage stats={hourlyUsageMock} />
            <PopularQuestions questions={popularQuestionsMock} />

            <MissingDocumentAreas areas={missingDocumentAreasMock} />
          </section>

        </main>

      </div>

    </div>
  );
}

export default AdminDashboard;
