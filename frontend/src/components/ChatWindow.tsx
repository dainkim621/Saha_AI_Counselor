import {
  useEffect,
  useRef,
} from "react";

import type { Message } from "../App";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
};

function ChatWindow({
  messages,
  isLoading,
}: ChatWindowProps) {
  const bottomRef =
    useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
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
          <div className="message-bubble assistant-bubble">
            답변을 생성하고 있어요...
          </div>
        </div>
      )}

      <div ref={bottomRef}></div>
    </div>
  );
}

export default ChatWindow;