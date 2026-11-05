import type { HourlyUsageStat } from "../../types/adminDashboard";

type HourlyUsageProps = {
  stats: HourlyUsageStat[];
};

function HourlyUsage({ stats }: HourlyUsageProps) {
  // 가장 이용량이 많은 시간대의 질문 수
  const maxCount = Math.max(
    1,
    ...stats.map((item) => item.count)
  );

  return (
    <section className="dashboard-card dashboard-card-wide">
      <h2>시간대별 이용량</h2>

      <div className="hourly-usage-list">
        {stats.map((item) => {
          // 질문 수가 가장 많은 시간대인지 확인
          // 질문이 0건인 경우에는 강조하지 않음
          // 질문데이터가 없는 시간대도 오류 안남
          const isPeakHour =
            item.count === maxCount && item.count > 0;

          return (
            <div className="hourly-usage-item" key={item.hour}>
              <span className="hourly-usage-hour">
                {item.hour}
              </span>

              <div className="hourly-usage-bar">
                <div
                  className="hourly-usage-fill"
                  style={{
                    width: `${(item.count / maxCount) * 100}%`,

                    backgroundColor: isPeakHour
                      ? "#171717"  // 가장 많은 시간대: 검정색
                      : "#A3A3A3", // 나머지 시간대: 연한 회색
                  }}
                />
              </div>

              <span className="hourly-usage-count">
                {item.count.toLocaleString()}건
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

export default HourlyUsage;
