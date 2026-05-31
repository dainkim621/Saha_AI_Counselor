import { useState } from "react";
import "./App.css";

import Header from "./components/Header";
import MascotCard from "./components/MascotCard";
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

    try {
  const response = await fetch(
    "http://localhost:8000/ai-chat",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        question: question,
      }),
    }
  );


  // ✅ 추가: 백엔드 응답이 실패했는지 확인
  if (!response.ok) {
    throw new Error("백엔드 응답 오류");
  }

  const data = await response.json();

  const aiMessage: Message = {
    role: "assistant",
    content: data.answer,
  };

  setMessages((prev) => [...prev, aiMessage]);
} catch (error) {
  const errorMessage: Message = {
    role: "assistant",
    content:
      "서버 연결 중 오류가 발생했습니다.",
  };

  setMessages((prev) => [...prev, errorMessage]);
} finally {
  setIsLoading(false);
}
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