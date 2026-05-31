import { useEffect, useRef, useState } from "react";
import type { Message } from "../App";
import gouni from "../assets/gouni-profile.png";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
};

function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);
  const lastSpokenIndexRef = useRef<number>(-1);
  const [isTtsOn, setIsTtsOn] = useState(false);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  useEffect(() => {
    if (!isTtsOn) {
      window.speechSynthesis?.cancel();
      return;
    }

    if (messages.length === 0) return;

    const lastIndex = messages.length - 1;
    const lastMessage = messages[lastIndex];

    if (lastMessage.role !== "assistant") return;
    if (lastSpokenIndexRef.current === lastIndex) return;
    if (!("speechSynthesis" in window)) return;

    lastSpokenIndexRef.current = lastIndex;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(lastMessage.content);

    utterance.lang = "ko-KR";
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  }, [messages, isTtsOn]);

  const handleToggleTts = () => {
    setIsTtsOn((prev) => {
      const next = !prev;

      if (!next && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }

      return next;
    });
  };

  return (
    <div className="chat-window">
      <button
        type="button"
        className={isTtsOn ? "tts-toggle tts-on" : "tts-toggle"}
        onClick={handleToggleTts}
      >
        {isTtsOn ? "🔊 음성 ON" : "🔇 음성 OFF"}
      </button>

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