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

  const getBotResponse = (input: string) => {
    const normalizedInput = input.trim().toLowerCase();

    if (normalizedInput.includes("전입신고")) {
      return "전입신고는 정부24 온라인 신청 또는 주민센터 방문으로 진행할 수 있어요. 원하시면 준비물과 절차도 함께 안내해드릴게요.";
    }

    if (normalizedInput.includes("주민센터")) {
      return "주민센터 위치 안내가 필요하시군요. 가까운 행정복지센터 위치와 운영시간을 확인할 수 있도록 도와드릴게요.";
    }

    if (normalizedInput.includes("복지")) {
      return "복지 서비스는 아동, 어르신, 장애인, 저소득층 지원 등으로 나뉘어요. 원하시는 대상에 맞춰 더 자세히 안내해드릴 수 있어요.";
    }

    if (normalizedInput.includes("서류") || normalizedInput.includes("발급")) {
      return "서류 발급은 정부24 또는 무인민원발급기, 주민센터 방문을 통해 가능해요. 필요한 서류 종류를 말씀해주시면 더 자세히 설명드릴게요.";
    }

    if (normalizedInput.includes("교통") || normalizedInput.includes("주차")) {
      return "교통 및 주차 정보가 필요하시군요. 공영주차장 위치, 운영시간, 요금 안내를 도와드릴 수 있어요.";
    }

    if (normalizedInput.includes("시설") || normalizedInput.includes("예약")) {
      return "공공시설 예약은 시설별 운영 정책에 따라 달라질 수 있어요. 체육시설, 강의실, 문화공간 중 어떤 시설인지 알려주시면 더 자세히 안내해드릴게요.";
    }

    return `"${input}"에 대해 안내해드릴게요. 현재는 프론트 테스트 단계라 예시 답변을 보여주고 있어요.`;
  };

  const handleSendMessage = (input: string) => {
    if (!input.trim()) return;

    const userMessage: Message = {
      id: Date.now(),
      text: input,
      sender: "user",
    };

    const botMessage: Message = {
      id: Date.now() + 1,
      text: getBotResponse(input),
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
          <QuickMenu onMenuClick={handleSendMessage} />
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