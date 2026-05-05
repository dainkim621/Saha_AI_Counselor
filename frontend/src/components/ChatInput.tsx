import { useState } from "react";

type ChatInputProps = {
  onSend: (message: string) => void;
  isLoading: boolean;
};

function ChatInput({ onSend, isLoading }: ChatInputProps) {
  const [input, setInput] = useState("");

  const handleSend = () => {
    const trimmedInput = input.trim();

    if (!trimmedInput) return;
    if (isLoading) return;

    onSend(trimmedInput);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
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

      <button onClick={handleSend} disabled={isLoading || !input.trim()}>
        {isLoading ? "답변 중..." : "전송"}
      </button>
    </div>
  );
}

export default ChatInput;