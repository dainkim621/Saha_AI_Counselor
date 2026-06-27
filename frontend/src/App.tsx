import { useEffect, useRef, useState } from "react";
import "./App.css";

import Header from "./components/Header";
import MascotCard from "./components/MascotCard";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

export type Message = {
  role: "user" | "assistant";
  content: string;
  files?: { file_name: string; file_url: string }[];
};

type SpeechRecognitionType = {
  lang: string;
  interimResults: boolean;
  continuous: boolean;
  start: () => void;
  stop: () => void;
  onresult: ((event: SpeechRecognitionEvent) => void) | null;
  onend: (() => void) | null;
  onerror: (() => void) | null;
};

type SpeechRecognitionEvent = {
  results: {
    [index: number]: {
      [index: number]: {
        transcript: string;
      };
    };
  };
};

type SpeechRecognitionConstructor = new () => SpeechRecognitionType;

declare global {
  interface Window {
    SpeechRecognition?: SpeechRecognitionConstructor;
    webkitSpeechRecognition?: SpeechRecognitionConstructor;
  }
}

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
  const [input, setInput] = useState("");

  const [fontLevel, setFontLevel] = useState(2);

  const [isTtsOn, setIsTtsOn] = useState(false);
  const [isListening, setIsListening] = useState(false);

  const lastSpokenIndexRef = useRef<number>(-1);
  const recognitionRef = useRef<SpeechRecognitionType | null>(null);

  const cleanTextForTTS = (text: string) => {
    return text
      // 이미지 링크: ![이름](주소) → 이름
      .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")

      // 하이퍼링크: [여권주소.pdf](https://...) → 여권주소.pdf
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")

      // 범위 표현 단위별 처리
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*일/g, "$1일에서 $2일")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*주/g, "$1주에서 $2주")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*개월/g, "$1개월에서 $2개월")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*시간/g, "$1시간에서 $2시간")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*분/g, "$1분에서 $2분")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*년/g, "$1년에서 $2년")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*월/g, "$1월에서 $2월")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*개/g, "$1개에서 $2개")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*명/g, "$1명에서 $2명")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*건/g, "$1건에서 $2건")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*회/g, "$1회에서 $2회")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*원/g, "$1원에서 $2원")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*층/g, "$1층에서 $2층")
      .replace(/(\d+)\s*[~-]\s*(\d+)\s*시/g, "$1시에서 $2시")

      // 전화기 이모티콘 제거
      .replace(/[☎📞📱]/g, "")

      // 볼드/이탤릭 제거
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")

      // 코드 기호 제거
      .replace(/`([^`]+)`/g, "$1")

      // 제목, 목록 기호 제거
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/^\s*[-*+]\s+/gm, "")

      // 남은 URL 제거
      .replace(/https?:\/\/\S+/g, "")

      // 남은 마크다운 특수문자 제거
      .replace(/[*_~>#]/g, "")

      .trim();
  };

  const speakText = (text: string) => {
    if (!("speechSynthesis" in window)) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(cleanTextForTTS(text));
    utterance.lang = "ko-KR";
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  };

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

    lastSpokenIndexRef.current = lastIndex;
    speakText(lastMessage.content);
  }, [messages, isTtsOn]);

  const handleStartStt = () => {
    if (isLoading) return;

    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("현재 브라우저에서는 음성 인식을 지원하지 않습니다.");
      return;
    }

    if (isListening) {
      recognitionRef.current?.stop();
      setIsListening(false);
      return;
    }

    const recognition = new SpeechRecognition();

    recognition.lang = "ko-KR";
    recognition.interimResults = false;
    recognition.continuous = false;

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript.trim();

      if (!transcript) return;

      setInput(transcript);
      speakText(transcript);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.onerror = () => {
      setIsListening(false);
      speakText("음성 인식 중 오류가 발생했습니다.");
    };

    recognitionRef.current = recognition;
    setIsListening(true);
    recognition.start();
  };

  const handleToggleTts = () => {
    setIsTtsOn((prev) => {
      const next = !prev;

      if (!next && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }

      return next;
    });
  };

  const handleReplayTts = () => {
    const lastAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");

    if (!lastAssistantMessage) return;

    speakText(lastAssistantMessage.content);
  };

  const sendMessage = async (question: string) => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) return;
    if (isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: trimmedQuestion,
    };

    const history = messages
      .filter(
        (message) =>
          message.content !== "안녕하세요! 사하구 민원 상담을 도와드릴게요."
      )
      .map((message) => ({
        role: message.role,
        content: message.content,
      }));

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/ai-chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          history: history, // 밀리지 않은 대화 이력이 전달
        }),
      });

      if (!response.ok) {
        throw new Error("백엔드 응답 오류");
      }

      const data = await response.json();

      const aiMessage: Message = {
        role: "assistant",
        content: data.answer,
        files: data.files,
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      const errorMessage: Message = {
        role: "assistant",
        content: "서버 연결 중 오류가 발생했습니다.",
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
        <div className="voice-accessibility-controls">
          <button
            type="button"
            className={isListening ? "voice-button active" : "voice-button"}
            onClick={handleStartStt}
            disabled={isLoading}
          >
            {isListening ? "🎙️ 듣는 중" : "🎤 음성 입력"}
          </button>

          <button
            type="button"
            className={isTtsOn ? "voice-button active" : "voice-button"}
            onClick={handleToggleTts}
          >
            {isTtsOn ? "🔊 답변 음성 ON" : "🔇 답변 음성 OFF"}
          </button>

          <button
            type="button"
            className="voice-button"
            onClick={handleReplayTts}
          >
            ↻ 다시 듣기
          </button>
        </div>

        <div className="font-controls">
          <span>글자 크기</span>
          <button onClick={decreaseFont}>－</button>
          <div className="font-label">{fontLabels[fontLevel]}</div>
          <button onClick={increaseFont}>＋</button>
        </div>
      </div>

      <main className="main-layout">
        <section className="left-section">
          <MascotCard />
        </section>

        <section className="chat-section">
          <ChatWindow messages={messages} isLoading={isLoading} />

          <ChatInput
            input={input}
            setInput={setInput}
            onSend={sendMessage}
            isLoading={isLoading}
          />
        </section>
      </main>
    </div>
  );
}

export default App;