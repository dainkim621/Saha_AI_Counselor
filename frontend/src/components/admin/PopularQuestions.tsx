import type { PopularQuestion } from "../../types/adminDashboard";

type PopularQuestionsProps = {
  questions: PopularQuestion[];
};

function PopularQuestions({ questions }: PopularQuestionsProps) {
  return (
    <section className="dashboard-card dashboard-card-wide">
      <h2>자주 묻는 질문 TOP5</h2>

      <div className="popular-question-list">
        {questions.map((item, index) => (
          <div className="popular-question-item" key={item.id}>
            <span className="popular-question-rank">
              {index + 1}
            </span>

            <span className="popular-question-text">
              {item.question}
            </span>

            <strong className="popular-question-count">
              {item.count.toLocaleString()}건
            </strong>
          </div>
        ))}
      </div>
    </section>
  );
}

export default PopularQuestions;