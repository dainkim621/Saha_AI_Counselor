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

      <button
        onClick={handleSend}
        disabled={isLoading || !input.trim()}
      >
        {isLoading ? "답변 중..." : "전송"}
      </button>
    </div>
  );
}

export default ChatInput;