import type { LanguageStat } from "../../types/adminDashboard";

type LanguageStatsProps = {
  stats: LanguageStat[];
};

function LanguageStats({ stats }: LanguageStatsProps) {
  return (
    <section className="dashboard-card">
      <h2>언어별 질문 비율</h2>

      <div className="language-stats-list">
        {stats.map((item) => (
          <div className="language-stat-item" key={item.language}>
            <div className="language-stat-header">
              <span>{item.language}</span>

              <span>
                {item.count.toLocaleString()}건 ({item.percentage}%)
              </span>
            </div>

            <div className="language-stat-bar">
              <div
                className="language-stat-fill"
                style={{ width: `${item.percentage}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

export default LanguageStats;