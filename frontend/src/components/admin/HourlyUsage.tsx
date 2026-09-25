import type { HourlyUsageStat } from "../../types/adminDashboard";

type HourlyUsageProps = {
  stats: HourlyUsageStat[];
};

function HourlyUsage({ stats }: HourlyUsageProps) {
  // 가장 이용량이 많은 시간의 질문 수
  // 막대 길이를 계산할 때 기준으로 사용
  const maxCount = Math.max(...stats.map((item) => item.count));

  return (
    <section className="dashboard-card dashboard-card-wide">
      <h2>시간대별 이용량</h2>

      <div className="hourly-usage-list">
        {stats.map((item) => (
          <div className="hourly-usage-item" key={item.hour}>
            <span className="hourly-usage-hour">
              {item.hour}
            </span>

            <div className="hourly-usage-bar">
              <div
                className="hourly-usage-fill"
                style={{
                  width: `${(item.count / maxCount) * 100}%`,
                }}
              />
            </div>

            <span className="hourly-usage-count">
              {item.count.toLocaleString()}건
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

export default HourlyUsage;