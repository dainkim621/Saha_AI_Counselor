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

  const sendMessage = async (question: string) => {
    if (!question.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: question,
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/ai-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question,
        }),
      });

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
      console.error(error);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "서버와 연결하는 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="app">
      <Header />

      <main className="main-layout">
        <section className="left-section">
          <MascotCard />
          <QuickMenu onSelect={sendMessage} />
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