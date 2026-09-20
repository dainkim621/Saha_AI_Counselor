// 관리자 페이지에서 사용할 CSS 불러오기
import "../styles/AdminDashboard.css";

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

        {/* 최근 7일 질문 수 */}
        <div className="dashboard-card">
          최근 7일 질문 수
        </div>

        {/* 답변 실패 질문 */}
        <div className="dashboard-card">
          답변 실패 질문
        </div>

        {/* 언어별 질문 비율 */}
        <div className="dashboard-card">
          언어별 질문 비율
        </div>

        {/* 시간대별 이용량 */}
        <div className="dashboard-card">
          시간대별 이용량
        </div>

        {/* 자주 묻는 질문 TOP5 (가로로 넓게 표시) */}
        <div className="dashboard-card dashboard-card-wide">
          자주 묻는 질문 TOP5
        </div>

        {/* 문서 보완이 필요한 분야 (가로로 넓게 표시) */}
        <div className="dashboard-card dashboard-card-wide">
          문서 보완 필요 분야
        </div>

      </section>

    </main>
  );
}

export default AdminDashboard;