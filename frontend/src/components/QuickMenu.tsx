// QuickMenu 컴포넌트가 받을 props 타입 정의
type QuickMenuProps = {
  /*
   * FAQ 버튼을 클릭했을 때
   * 선택한 질문을 App.tsx의 sendMessage 함수로 전달
   */
  onSelect: (message: string) => void;

  /*
   * 챗봇이 답변을 생성 중인지 여부
   *
   * true이면 FAQ 버튼을 비활성화하여
   * 질문이 중복 전송되는 것을 방지
   */
  disabled: boolean;

  /*
   * 화면에 표시할 FAQ 질문 목록
   *
   * App.tsx에서 localStorage의 최근 7일 질문 기록을
   * 집계한 결과를 배열 형태로 전달받음
   */
  questions: string[];
};

// QuickMenu 컴포넌트
function QuickMenu({
  questions,
  onSelect,
  disabled,
}: QuickMenuProps) {
  return (
    // 자주 묻는 질문 전체 영역
    <div className="quick-menu">
      {/* QuickMenu 상단 제목 영역 */}
      <div className="quick-menu-header">
        {/* 자주 묻는 질문 제목 */}
        <h3>🔥 이번 주 자주 묻는 질문</h3>

        {/* 질문을 집계한 기간 안내 */}
        <span>최근 7일 기준</span>
      </div>

      {/* FAQ 질문 버튼 목록 */}
      <div className="quick-button-list">
        {questions.length > 0 ? (
          /*
           * 전달받은 질문 배열을 순회하면서
           * 질문마다 하나의 버튼을 생성
           */
          questions.map((question, index) => (
            <button
              /*
               * 질문 내용과 배열 순서를 함께 key로 사용
               *
               * 같은 질문이 중복으로 들어오더라도
               * React key가 겹치는 것을 방지
               */
              key={`${question}-${index}`}
              type="button"

              /*
               * 버튼 스타일 적용
               *
               * 번호와 질문 내용을 가로로 배치하고
               * 두 요소 사이에 간격을 주기 위한 클래스
               */
              className="quick-menu-button"

              /*
               * 버튼을 클릭하면 선택한 질문을
               * App.tsx의 onSelect 함수로 전달
               */
              onClick={() => onSelect(question)}

              /*
               * 챗봇이 답변을 생성 중일 때는
               * 버튼을 클릭할 수 없도록 비활성화
               */
              disabled={disabled}
            >
              {/* 실제 질문 내용 */}
              <span className="quick-question-text">
                {question}
              </span>
            </button>
          ))
        ) : (
          /*
           * 전달받은 질문 배열이 비어 있을 경우
           * FAQ 버튼 대신 안내 문구 표시
           */
          <p className="quick-menu-empty">
            아직 집계된 질문이 없습니다.
          </p>
        )}
      </div>
    </div>
  );
}

export default QuickMenu;