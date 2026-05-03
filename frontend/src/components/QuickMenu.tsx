type QuickMenuProps = {
  onSelect: (message: string) => void;
};

const quickQuestions = [
  "전입신고는 어떻게 하나요?",
  "여권 발급에 필요한 서류는 무엇인가요?",
  "무인민원발급기는 어디에 있나요?",
  "대형폐기물 배출은 어떻게 신청하나요?",
];

function QuickMenu({ onSelect }: QuickMenuProps) {
  return (
    <div className="quick-menu">
      <h3>자주 묻는 질문</h3>

      <div className="quick-button-list">
        {quickQuestions.map((question) => (
          <button key={question} onClick={() => onSelect(question)}>
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

export default QuickMenu;