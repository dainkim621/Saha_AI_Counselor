import { useEffect, useRef } from "react";
import type { Message } from "../App";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
};

function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  // 메시지가 추가되거나 로딩 상태가 바뀌면 맨 아래로 자동 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      {messages.map((message, index) => (
        <div
          key={index}
          className={
            message.role === "user"
              ? "message-row user-row"
              : "message-row assistant-row"
          }
        >
          <div
            className={
              message.role === "user"
                ? "message-bubble user-bubble"
                : "message-bubble assistant-bubble"
            }
          >
            {message.content}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="message-row assistant-row">
          <div className="message-bubble assistant-bubble loading-bubble">
            답변을 생성하고 있어요<span className="loading-dots">...</span>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

export default ChatWindow;