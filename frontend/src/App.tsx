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

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "안녕하세요! 사하구 민원 상담을 도와드릴게요.",
    },
  ]);

  const [isLoading, setIsLoading] = useState(false);

  // 현재는 백엔드 없이 mock 답변으로 프론트 동작 확인
  const sendMessage = async (question: string) => {
    if (!question.trim()) return;
    if (isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    setTimeout(() => {
      const mockAnswer: Message = {
        role: "assistant",
        content:
          "현재는 프론트엔드 테스트용 임시 답변입니다.\n\n백엔드 연결 후에는 이곳에 실제 사하구 민원 안내 답변이 표시됩니다.",
      };

      setMessages((prev) => [...prev, mockAnswer]);
      setIsLoading(false);
    }, 800);
  };

  return (
    <div className="app">
      <Header />

      <main className="main-layout">
        <section className="left-section">
          <MascotCard />
          <QuickMenu onSelect={sendMessage} disabled={isLoading} />
        </section>

        <section className="chat-section">
          <ChatWindow messages={messages} isLoading={isLoading} />
          <ChatInput onSend={sendMessage} isLoading={isLoading} />
        </section>
      </main>
    </div>
  );
}

export default App;