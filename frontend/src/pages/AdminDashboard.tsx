// 관리자 페이지에서 사용할 CSS 불러오기
import "../styles/AdminDashboard.css";
import { useNavigate } from "react-router-dom";

import SummaryCards from "../components/admin/SummaryCards";
import FailedQuestions from "../components/admin/FailedQuestions";
import LanguageStats from "../components/admin/LanguageStats";
import HourlyUsage from "../components/admin/HourlyUsage";
import PopularQuestions from "../components/admin/PopularQuestions";
import MissingDocumentAreas from "../components/admin/MissingDocumentAreas";

import {
  dashboardSummaryMock,
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
    // 관리자 페이지 전체 영역
    <main className="admin-dashboard">

      {/* 페이지 제목 */}
      <header className="admin-dashboard-header">
        <h1>관리자 질문 분석 대시보드</h1>

        <p>
          사용자 질문 통계와 답변 품질을 관리합니다.
        </p>

        <button
          type="button"
          onClick={handleLogout}
        >
          로그아웃
        </button>
      </header>

      {/* 카드들을 배치하는 영역 */}
      <section className="dashboard-grid">
        <SummaryCards
        totalQuestions={dashboardSummaryMock.totalQuestions}
        failedQuestionCount={dashboardSummaryMock.failedQuestionCount}
        topLanguage={dashboardSummaryMock.topLanguage}
        peakHour={dashboardSummaryMock.peakHour}
        />

        <FailedQuestions questions={failedQuestionsMock} />
        <LanguageStats stats={languageStatsMock} />
        <HourlyUsage stats={hourlyUsageMock} />
        <PopularQuestions questions={popularQuestionsMock} />

        <MissingDocumentAreas areas={missingDocumentAreasMock} />
      </section>

    </main>
  );
}

export default AdminDashboard;