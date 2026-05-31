import { useEffect, useRef } from "react";
import type { Message } from "../App";
import gouni from "../assets/gouni-profile.png";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
};

function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const lastSpokenIndexRef = useRef<number>(-1);

  // 메시지가 추가되거나 로딩 상태가 바뀌면 자동으로 아래로 스크롤
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  // 마지막 assistant 메시지를 TTS로 읽기
  useEffect(() => {
    if (messages.length === 0) return;

    const lastIndex = messages.length - 1;
    const lastMessage = messages[lastIndex];

    // assistant 답변이 아니면 읽지 않음
    if (lastMessage.role !== "assistant") return;

    // 같은 메시지를 중복으로 읽지 않도록 방지
    if (lastSpokenIndexRef.current === lastIndex) return;

    // 브라우저가 TTS를 지원하지 않으면 실행하지 않음
    if (!("speechSynthesis" in window)) return;

    lastSpokenIndexRef.current = lastIndex;

    // 이전에 읽고 있던 음성이 있으면 중지
    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(lastMessage.content);

    utterance.lang = "ko-KR";
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  }, [messages]);

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
            {message.content}
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