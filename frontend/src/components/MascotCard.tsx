import gouni from "../assets/gouni-mascot.png";

type MascotCardProps = {
  onSelectQuestion: (question: string) => void;
};

const faqQuestions = [
  "주민등록등본은 어떻게 발급하나요?",
  "전입신고는 어디서 하나요?",
  "여권 재발급은 어떻게 신청하나요?",
  "대형폐기물은 어떻게 배출하나요?",
  "가족관계증명서는 어디서 발급받나요?",
];

function MascotCard({
  onSelectQuestion,
}: MascotCardProps) {
  return (
    <div className="mascot-card">
      <div className="mascot-glow">
        <img
          src={gouni}
          alt="사하구 캐릭터 고우니"
          className="gouni-main"
        />
      </div>

      <div className="mascot-text">
        <span className="mascot-label">
          사하구 AI 챗봇
        </span>

        <h2>고우니</h2>

        <p>
          필요한 민원 정보를 찾기 쉽게
          정리해서 안내해드릴게요.
        </p>
      </div>

      <div className="faq-section">
        <h3>자주 묻는 질문</h3>

        {faqQuestions.map((question, index) => (
          <button
            key={index}
            className="faq-button"
            onClick={() =>
              onSelectQuestion(question)
            }
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

export default MascotCard;