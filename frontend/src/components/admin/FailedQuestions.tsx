import type { FailedQuestion } from "../../types/adminDashboard";

type FailedQuestionsProps = {
  questions: FailedQuestion[];
};

function FailedQuestions({ questions }: FailedQuestionsProps) {
  return (
    <section className="dashboard-card">
      <h2>답변 실패 질문</h2>

      <div className="failed-question-list">
        {questions.map((item) => (
          <article className="failed-question-item" key={item.id}>
            <strong className="failed-question-text">
              {item.question}
            </strong>

            <span className="failed-question-reason">
              {item.reason}
            </span>

            <time className="failed-question-time">
              {item.createdAt}
            </time>
          </article>
        ))}
      </div>
    </section>
  );
}

export default FailedQuestions;