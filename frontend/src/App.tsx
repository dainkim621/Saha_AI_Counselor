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

    // 1. 사용자가 입력한 메시지를 화면에 추가
    const userMessage: Message = {
      role: "user",
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      // 2. 수빈님이 만든 FastAPI 백엔드 API 호출
      const response = await fetch("http://127.0.0.1:8000/ai-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ question: question }), // ChatRequest 규격 (question)
      });

      if (!response.ok) {
        throw new Error("서버 응답 오류");
      }

      const data = await response.json();

      // 3. 백엔드에서 받아온 실제 AI 답변을 화면에 추가
      const aiMessage: Message = {
        role: "assistant",
        content: data.answer, // 수빈님 백엔드 응답 규격 (answer)
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("백엔드 통신 실패:", error);
      
      // 에러 발생 시 화면에 표시할 안내 메시지
      const errorMessage: Message = {
        role: "assistant",
        content: "죄송합니다. 현재 서버 연결에 문제가 발생했습니다. 백엔드가 켜져 있는지 확인해 주세요.",
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