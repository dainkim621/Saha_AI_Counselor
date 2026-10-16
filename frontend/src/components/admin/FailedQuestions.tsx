import type { FailedQuestion } from "../../types/adminDashboard";

type FailedQuestionsProps = {
  questions: FailedQuestion[];
};

// DB의 영문 카테고리 코드를 한글 말머리로 변환
const getCategoryLabel = (category?: string) => {
  switch (category) {
    case "NO_INFO":
      return "[정보 없음]";
    case "OUT_OF_DOMAIN":
      return "[관련 없음]";
    case "INAPPROPRIATE":
      return "[부적절함]";
    case "NONE":
      return "";
    default:
      return category ? `[${category}]` : "[기타]";
  }
};

function FailedQuestions({ questions }: FailedQuestionsProps) {
  return (
    <section className="dashboard-card">
      <h2>답변 실패 질문</h2>

      <div className="failed-question-list">
        {questions.map((item) => {
          // 카테고리와 사유를 "타입: 이유" 형태로 결합
          const categoryLabel = getCategoryLabel(item.category);
          const displayReason = categoryLabel 
            ? `${categoryLabel} ${item.reason}` 
            : item.reason;

          return (
            <article className="failed-question-item" key={item.id}>
              <strong className="failed-question-text">
                {item.question}
              </strong>

              <span className="failed-question-reason">
                {displayReason}
              </span>

              <time className="failed-question-time">
                {item.createdAt}
              </time>
            </article>
          );
        })}
      </div>
    </section>
  );
}

export default FailedQuestions;