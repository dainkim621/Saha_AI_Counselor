import { useState } from "react";
import Header from "./components/Header";
import MascotCard from "./components/MascotCard";
import QuickMenu from "./components/QuickMenu";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

type Message = {
  id: number;
  text: string;
  sender: "user" | "bot";
};

function App() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 1,
      text: "안녕하세요. 사하구 AI 챗봇 고우니예요! 무엇을 도와드릴까요?",
      sender: "bot",
    },
  ]);

  const handleSendMessage = (input: string) => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now(),
      text: input,
      sender: "user",
    };

    const botMessage: Message = {
      id: Date.now() + 1,
      text: `"${input}"에 대해 안내해드릴게요. 현재는 프론트 테스트 단계라 예시 답변을 보여주고 있어요.`,
      sender: "bot",
    };

    setMessages((prev) => [...prev, userMessage, botMessage]);
  };

  return (
    <div className="min-h-screen bg-slate-50">
      <Header />

      <main className="mx-auto flex max-w-7xl flex-col gap-6 p-4 lg:flex-row">
        <section className="flex flex-col gap-4 lg:w-1/3">
          <MascotCard />
          <QuickMenu />
        </section>

        <section className="flex-1 rounded-3xl bg-white p-4 shadow">
          <ChatWindow messages={messages} />
          <ChatInput onSendMessage={handleSendMessage} />
        </section>
      </main>
    </div>
  );
}

export default App;