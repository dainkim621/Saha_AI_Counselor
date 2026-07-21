// QuickMenu 컴포넌트가 받을 데이터 타입
type QuickMenuProps = {
  // 버튼 클릭 시 선택한 질문을 App.tsx로 전달
  onSelect: (message: string) => void;

  // 현재 답변 생성 중이면 버튼 비활성화
  disabled: boolean;

  // 화면에 표시할 FAQ 질문 목록
  questions: string[];
};

function QuickMenu({
  questions,
  onSelect,
  disabled,
}: QuickMenuProps) {
  return (
    <div className="quick-menu">
      {/* FAQ 제목 */}
      <h3>자주 묻는 질문</h3>

      <div className="quick-button-list">
        {/* 전달받은 FAQ 목록을 버튼으로 생성 */}
        {questions.map((question) => (
          <button
            key={question}
            type="button"
            // 버튼 클릭 시 해당 질문을 App.tsx로 전달
            onClick={() => onSelect(question)}
            // 답변 생성 중에는 클릭 방지
            disabled={disabled}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}

export default QuickMenu;