import type { SatisfactionStat } from "../../types/adminDashboard";

type SatisfactionStatsProps = {
  stats: SatisfactionStat | null;
};

function SatisfactionStats({ stats }: SatisfactionStatsProps) {
  return (
    <section className="dashboard-card satisfaction-card">
      <h2>사용자 만족도 현황</h2>

      {!stats ? (
        <p>만족도 데이터를 불러오는 중...</p>
      ) : (
        <>
          <div className="satisfaction-stats-grid">
            <div className="satisfaction-stat-item">
              <span>긍정 평가</span>
              <strong>
                {stats.positiveCount.toLocaleString()}건
              </strong>
            </div>

            <div className="satisfaction-stat-item">
              <span>부정 평가</span>
              <strong>
                {stats.negativeCount.toLocaleString()}건
              </strong>
            </div>
          </div>

          <div className="satisfaction-rate-header">
            <span>긍정 평가 비율</span>
            <strong>
              {stats.totalCount > 0
                ? `${stats.positiveRate.toFixed(1)}%`
                : "평가 없음"}
            </strong>
          </div>

          <div className="satisfaction-progress">
            <div
              className="satisfaction-progress-fill"
              style={{
                width: `${Math.min(100, Math.max(0, stats.positiveRate))}%`,
              }}
            />
          </div>

          <p className="satisfaction-description">
            전체 기간 · 만족도 평가 참여 건수 기준
          </p>
        </>
      )}
    </section>
  );
}

export default SatisfactionStats;