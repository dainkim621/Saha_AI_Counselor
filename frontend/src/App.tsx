import { useState } from "react";
import "./App.css";

import Header from "./components/Header";
import MascotCard from "./components/MascotCard";
import QuickMenu from "./components/QuickMenu";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

export type Message = {
  role: "user" | "assistant";
  content: string;
};

const fontModes = [
  "font-xsmall",
  "font-small",
  "font-normal",
  "font-large",
  "font-xlarge",
];

const fontLabels = [
  "아주 작게",
  "작게",
  "기본",
  "크게",
  "아주 크게",
];

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "안녕하세요! 사하구 민원 상담을 도와드릴게요.",
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);

  // 기본 = 2
  const [fontLevel, setFontLevel] = useState(2);

  const sendMessage = async (question: string) => {
    if (!question.trim()) return;
    if (isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    // mock 답변
    setTimeout(() => {
      const aiMessage: Message = {
        role: "assistant",
        content:
          "현재는 프론트엔드 테스트용 임시 답변입니다.\n\n백엔드 연결 후 실제 민원 안내 답변이 표시됩니다.",
      };

      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    }, 800);
  };

  const decreaseFont = () => {
    setFontLevel((prev) => Math.max(prev - 1, 0));
  };

  const increaseFont = () => {
    setFontLevel((prev) => Math.min(prev + 1, 4));
  };

  return (
    <div className={`app ${fontModes[fontLevel]}`}>
      <Header />

      <div className="accessibility-bar">
        <span>글자 크기</span>

        <button onClick={decreaseFont}>－</button>

        <div className="font-label">
          {fontLabels[fontLevel]}
        </div>

        <button onClick={increaseFont}>＋</button>
      </div>

      <main className="main-layout">
        <section className="left-section">
          <MascotCard />
          <QuickMenu
            onSelect={sendMessage}
            disabled={isLoading}
          />
        </section>

        <section className="chat-section">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
          />

          <ChatInput
            onSend={sendMessage}
            isLoading={isLoading}
          />
        </section>
      </main>
    </div>
  );
}

export default App;