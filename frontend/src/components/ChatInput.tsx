
type ChatInputProps = {
  input: string;
  setInput: React.Dispatch<React.SetStateAction<string>>;
  onSend: (message: string) => void;
  isLoading: boolean;
};

function ChatInput({
  input,
  setInput,
  onSend,
  isLoading,
}: ChatInputProps) {
  const handleSend = () => {
    const trimmedInput = input.trim();

    if (!trimmedInput) return;
    if (isLoading) return;

    onSend(trimmedInput);
  };

  const handleKeyDown = (
    e: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (e.key === "Enter") {
      handleSend();
    }
  };

  return (
    <div className="chat-input-box">
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="궁금한 민원 내용을 입력하세요"
        disabled={isLoading}
      />

      {/* 종이비행기 전송 버튼 */}
      <button
        type="button"
        onClick={handleSend}
        disabled={isLoading || !input.trim()}
        title={isLoading ? "답변 생성 중" : "전송"}
        aria-label={isLoading ? "답변 생성 중" : "메시지 전송"}
      >
        {isLoading ? (
          // 답변 생성 중 로딩 아이콘
          <svg
            className="send-loading-icon"
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            aria-hidden="true"
          >
            <circle
              cx="12"
              cy="12"
              r="9"
              opacity="0.25"
            />
            <path d="M21 12a9 9 0 0 0-9-9" />
          </svg>
        ) : (
          // 기본 종이비행기 아이콘
          <svg
            width="22"
            height="22"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M22 2 11 13" />
            <path d="m22 2-7 20-4-9-9-4Z" />
          </svg>
        )}
      </button>
    </div>
  );
}

export default ChatInput;
