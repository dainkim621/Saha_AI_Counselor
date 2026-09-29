import type { DashboardSummary } from "../../types/adminDashboard";
function SummaryCards({
  totalQuestions,
  failedQuestionCount,
  topLanguage,
  peakHour,
}: DashboardSummary) {
  return (
    <section
      className="dashboard-summary-grid"
      aria-label="관리자 주요 통계"
    >
      <article className="dashboard-summary-card">
        <span className="dashboard-summary-label">
          최근 7일 질문 수
        </span>

        <strong className="dashboard-summary-value">
          {totalQuestions.toLocaleString()}건
        </strong>

        <span className="dashboard-summary-description">
          최근 7일 동안 접수된 전체 질문
        </span>
      </article>

      <article className="dashboard-summary-card">
        <span className="dashboard-summary-label">
          답변 실패 질문
        </span>

        <strong className="dashboard-summary-value">
          {failedQuestionCount}건
        </strong>

        <span className="dashboard-summary-description">
          관련 문서 또는 FAQ 보완 필요
        </span>
      </article>

      <article className="dashboard-summary-card">
        <span className="dashboard-summary-label">
          가장 많이 사용된 언어
        </span>

        <strong className="dashboard-summary-value dashboard-summary-text">
          {topLanguage}
        </strong>

        <span className="dashboard-summary-description">
          사용자 질문 기준
        </span>
      </article>

      <article className="dashboard-summary-card">
        <span className="dashboard-summary-label">
          이용량이 많은 시간
        </span>

        <strong className="dashboard-summary-value dashboard-summary-text">
          {peakHour}
        </strong>

        <span className="dashboard-summary-description">
          질문이 가장 많이 접수된 시간대
        </span>
      </article>
    </section>
  );
}

export default SummaryCards;