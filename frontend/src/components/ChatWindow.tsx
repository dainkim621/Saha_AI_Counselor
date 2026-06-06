import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../App";
import gouni from "../assets/gouni-profile.png";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
};

function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

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
          {message.role === "assistant" && (
            <img src={gouni} alt="고우니" className="chat-avatar" />
          )}

          <div
            className={
              message.role === "user"
                ? "message-bubble user-bubble"
                : "message-bubble assistant-bubble"
            }
          >
            {message.role === "assistant" ? (
              <ReactMarkdown>{message.content}</ReactMarkdown>
            ) : (
              message.content
            )}
          </div>
        </div>
      ))}

      {isLoading && (
        <div className="message-row assistant-row">
          <img
            src={gouni}
            alt="고우니 프로필"
            className="chat-avatar chat-avatar-active"
          />

          <div className="message-bubble assistant-bubble">
            고우니가 답변을 준비하고 있어요...
          </div>
        </div>
      )}

      <div ref={bottomRef}></div>
    </div>
  );
}

export default ChatWindow;