// 관리자 페이지에서 사용할 CSS 불러오기
import "../styles/AdminDashboard.css";

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
  return (
    // 관리자 페이지 전체 영역
    <main className="admin-dashboard">

      {/* 페이지 제목 */}
      <header className="admin-dashboard-header">
        <h1>관리자 질문 분석 대시보드</h1>

        <p>
          사용자 질문 통계와 답변 품질을 관리합니다.
        </p>
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