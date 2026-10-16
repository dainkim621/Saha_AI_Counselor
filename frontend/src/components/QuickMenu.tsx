// FAQ 접기·펼치기 상태 관리
import { useState } from "react";

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

  // FAQ 펼침 여부 (false: 접힘, true: 펼침)
  const [isOpen, setIsOpen] = useState(false);

  return (
    // 자주 묻는 질문 전체 영역
    <div className="quick-menu">
      {/* FAQ 접기·펼치기 버튼 */}
      <button
        type="button"
        className="quick-menu-toggle"
        onClick={() => setIsOpen((prev) => !prev)}
        aria-expanded={isOpen}
        aria-controls="quick-menu-list"
      >
        {/* FAQ 질문 아이콘 */}
        <span className="quick-menu-leading-icon" aria-hidden="true">
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <circle cx="12" cy="12" r="9" />
            <path d="M9.5 9a2.5 2.5 0 0 1 5 0c0 1.7-2.5 2-2.5 4" />
            <path d="M12 17h.01" />
          </svg>
        </span>

        {/* FAQ 메뉴 이름 */}
        <span className="quick-menu-title">
          자주 묻는 질문
        </span>

        {/* 접기·펼치기 화살표 */}
        <span
          className="quick-menu-arrow"
          aria-hidden="true"
        />
      </button>

      {/* 펼쳤을 때만 질문 목록 표시 */}
      {isOpen && (
        <div id="quick-menu-list" className="quick-button-list">

          {questions.length > 0 ? (
            // FAQ 질문 목록 생성
            questions.map((question, index) => (
              <button
                key={`${question}-${index}`}
                type="button"
                className="quick-menu-button"

                // 클릭한 질문을 챗봇에 전달
                onClick={() => onSelect(question)}

                // 답변 생성 중에는 중복 질문 방지
                disabled={disabled}
              >
                <span className="quick-question-text">
                  {question}
                </span>
              </button>
            ))
          ) : (
            // 질문 데이터가 없을 때 표시
            <p className="quick-menu-empty">
              아직 집계된 질문이 없습니다.
            </p>
          )}

        </div>
      )}

    </div>
  );
}

export default QuickMenu;