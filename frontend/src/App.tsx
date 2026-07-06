import { useEffect, useRef, useState } from "react";
import "./App.css";

import Header from "./components/Header";
import MascotCard from "./components/MascotCard";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

// FastAPI 백엔드 서버 주소
const BACKEND_URL = "http://localhost:8000";

// 채팅 메시지 데이터 구조
export type Message = {
  role: "user" | "assistant";
  content: string;
  files?: { file_name: string; file_url: string }[];
  similarityScore?: number;
};

// 글자 크기 단계별 CSS 클래스
const fontModes = [
  "font-xsmall",
  "font-small",
  "font-normal",
  "font-large",
  "font-xlarge",
];

// 화면에 표시되는 글자 크기 이름
const fontLabels = ["아주 작게", "작게", "기본", "크게", "아주 크게"];

function App() {
  // 채팅 메시지 목록
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "안녕하세요! 사하구 민원 상담을 도와드릴게요.",
    },
  ]);

  // 답변 생성 중 여부
  const [isLoading, setIsLoading] = useState(false);

  // 입력창 텍스트
  const [input, setInput] = useState("");

  // 글자 크기 단계
  const [fontLevel, setFontLevel] = useState(2);

  // TTS 음성 출력 ON/OFF
  const [isTtsOn, setIsTtsOn] = useState(false);

  // STT 음성 녹음 중 여부
  const [isListening, setIsListening] = useState(false);

  // RAG 유사도 점수
  const [similarityScore, setSimilarityScore] = useState<number | null>(null);

  // 이용 가이드 모달 표시 여부
  const [showGuide, setShowGuide] = useState(false);

  // 마지막으로 읽은 assistant 메시지 인덱스 저장
  const lastSpokenIndexRef = useRef<number>(-1);

  // STT 녹음 객체 저장
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // 마이크 스트림 저장
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // 녹음된 음성 조각 저장
  const audioChunksRef = useRef<Blob[]>([]);

  // TTS로 읽기 전 Markdown, 링크, 특수기호 제거
  const cleanTextForTTS = (text: string) => {
    return text
      .replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1")
      .replace(/\[([^\]]+)\]\([^)]+\)/g, "$1")
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
      .replace(/[☎📞📱]/g, "")
      .replace(/\*\*([^*]+)\*\*/g, "$1")
      .replace(/\*([^*]+)\*/g, "$1")
      .replace(/`([^`]+)`/g, "$1")
      .replace(/^#{1,6}\s+/gm, "")
      .replace(/^\s*[-*+]\s+/gm, "")
      .replace(/https?:\/\/\S+/g, "")
      .replace(/[*_~>#]/g, "")
      .trim();
  };

  // 텍스트를 음성으로 읽어주는 함수
  const speakText = (text: string) => {
    if (!("speechSynthesis" in window)) return;
    if (!text.trim()) return;

    window.speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(cleanTextForTTS(text));
    utterance.lang = "ko-KR";
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  };

  // TTS가 켜져 있을 때 assistant 답변이 완성되면 자동으로 읽기
  useEffect(() => {
    if (!isTtsOn) {
      window.speechSynthesis?.cancel();
      return;
    }

    if (isLoading) return;
    if (messages.length === 0) return;

    const lastIndex = messages.length - 1;
    const lastMessage = messages[lastIndex];

    if (lastMessage.role !== "assistant") return;
    if (!lastMessage.content.trim()) return;
    if (lastSpokenIndexRef.current === lastIndex) return;

    lastSpokenIndexRef.current = lastIndex;
    speakText(lastMessage.content);
  }, [messages, isTtsOn, isLoading]);

  // 마이크 사용 종료 처리
  const stopMicrophone = () => {
    mediaStreamRef.current?.getTracks().forEach((track) => {
      track.stop();
      console.log("마이크 트랙 종료:", track.readyState);
    });

    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
  };

  // 음성 입력 시작/종료 처리
  const handleStartStt = async () => {
    if (isLoading) return;

    if (isListening) {
      mediaRecorderRef.current?.stop();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      audioChunksRef.current = [];

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsListening(false);
        stopMicrophone();

        console.log("마이크 종료됨");

        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });

        const formData = new FormData();
        formData.append("audio", audioBlob, "voice.webm");

        try {
          const response = await fetch(`${BACKEND_URL}/stt`, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            throw new Error("STT 서버 응답 오류");
          }

          const data = await response.json();
          const transcript = data.text?.trim();

          if (!transcript) return;

          setInput(transcript);
          speakText(transcript);
        } catch (error) {
          speakText("음성 인식 중 오류가 발생했습니다.");
        } finally {
          mediaRecorderRef.current = null;
          audioChunksRef.current = [];
        }
      };

      setIsListening(true);
      mediaRecorder.start();

      // 최대 10초까지만 녹음
      setTimeout(() => {
        if (mediaRecorder.state === "recording") {
          mediaRecorder.stop();
        }
      }, 10000);
    } catch (error) {
      console.error("마이크 오류:", error);

      setIsListening(false);

      alert(
        `마이크 오류: ${
          error instanceof Error ? error.message : "알 수 없는 오류"
        }`
      );
    }
  };

  // 답변 음성 ON/OFF 전환
  const handleToggleTts = () => {
    setIsTtsOn((prev) => {
      const next = !prev;

      if (!next && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }

      return next;
    });
  };

  // 마지막 assistant 답변 다시 듣기
  const handleReplayTts = () => {
    const lastAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");

    if (!lastAssistantMessage) return;

    speakText(lastAssistantMessage.content);
  };

  // 사용자 질문을 백엔드로 전송하고 스트리밍 답변 수신
  const sendMessage = async (question: string) => {
    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) return;
    if (isLoading) return;

    const userMessage: Message = {
      role: "user",
      content: trimmedQuestion,
    };

    // 초기 인사말 제외 후 이전 대화 내역 전송
    const history = messages
      .filter(
        (message) =>
          message.content !== "안녕하세요! 사하구 민원 상담을 도와드릴게요."
      )
      .map((message) => ({
        role: message.role,
        content: message.content,
      }));

    // 사용자 메시지와 빈 assistant 메시지를 먼저 화면에 추가
    setMessages((prev) => [
      ...prev,
      userMessage,
      {
        role: "assistant",
        content: "",
        files: [],
      },
    ]);

    setInput("");
    setSimilarityScore(null);
    setIsLoading(true);

    try {
      const response = await fetch(`${BACKEND_URL}/ai-chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
          history: history,
        }),
      });

      if (!response.ok) {
        throw new Error("백엔드 응답 오류");
      }

      if (!response.body) {
        throw new Error("스트리밍 응답을 받을 수 없습니다.");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      let buffer = "";
      let isDone = false;

      while (!isDone) {
        const { value, done } = await reader.read();

        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        const events = buffer.split("\n\n");
        buffer = events.pop() || "";

        for (const event of events) {
          if (!event.startsWith("data: ")) continue;

          const data = event.replace("data: ", "").trim();

          if (data === "[DONE]") {
            isDone = true;
            break;
          }

          const parsed = JSON.parse(data);

          // 유사도 점수 수신
          if (parsed.type === "score") {
            const score = Number(parsed.content);
            setSimilarityScore(score);

            setMessages((prev) => {
              const updated = [...prev];
              const lastIndex = updated.length - 1;

              updated[lastIndex] = {
                ...updated[lastIndex],
                similarityScore: score,
              };

              return updated;
            });
          }

          // 답변 텍스트 스트리밍 수신
          if (parsed.type === "text") {
            setMessages((prev) => {
              const updated = [...prev];
              const lastIndex = updated.length - 1;

              updated[lastIndex] = {
                ...updated[lastIndex],
                content: updated[lastIndex].content + parsed.content,
              };

              return updated;
            });

            await new Promise((resolve) => setTimeout(resolve, 20));
          }

          // 첨부파일 정보 수신
          if (parsed.type === "files") {
            setMessages((prev) => {
              const updated = [...prev];
              const lastIndex = updated.length - 1;

              updated[lastIndex] = {
                ...updated[lastIndex],
                files: parsed.content,
              };

              return updated;
            });
          }

          if (parsed.type === "error") {
            throw new Error(parsed.content);
          }
        }
      }
    } catch (error) {
      setMessages((prev) => {
        const updated = [...prev];
        const lastIndex = updated.length - 1;

        updated[lastIndex] = {
          role: "assistant",
          content: "서버 연결 중 오류가 발생했습니다.",
        };

        return updated;
      });
    } finally {
      setIsLoading(false);
    }
  };

  // 글자 크기 줄이기
  const decreaseFont = () => {
    setFontLevel((prev) => Math.max(prev - 1, 0));
  };

  // 글자 크기 키우기
  const increaseFont = () => {
    setFontLevel((prev) => Math.min(prev + 1, 4));
  };

  return (
    <div className={`app ${fontModes[fontLevel]}`}>
      {/* 상단 헤더 */}
      <Header onGuideClick={() => setShowGuide(true)} />

      {/* 이용 가이드 모달 */}
      {showGuide && (
        <div className="guide-overlay" onClick={() => setShowGuide(false)}>
          <div className="guide-modal" onClick={(e) => e.stopPropagation()}>
            <div className="guide-modal-header">
              <h2>📖 이용 가이드</h2>
              <button
                type="button"
                className="guide-close-button"
                onClick={() => setShowGuide(false)}
              >
                ✕
              </button>
            </div>

            <p className="guide-intro">
              고우니 챗봇은 사하구 민원 정보를 쉽게 안내해주는 AI 상담사입니다.
            </p>

            <section className="guide-section">
              <h3>💬 이렇게 질문해보세요</h3>
              <ul>
                <li>전입신고는 어떻게 하나요?</li>
                <li>여권 발급 준비물이 뭐야?</li>
                <li>대형폐기물 배출 신청 방법 알려줘</li>
                <li>가족관계증명서 발급은 어디서 해?</li>
              </ul>
            </section>

            <section className="guide-section">
              <h3>🔊 사용할 수 있는 기능</h3>
              <ul>
                <li>음성 입력으로 질문하기</li>
                <li>챗봇 답변 음성으로 듣기</li>
                <li>마지막 답변 다시 듣기</li>
                <li>글자 크기 조절하기</li>
                <li>관련 첨부파일 다운로드하기</li>
              </ul>
            </section>

            <section className="guide-section">
              <h3>⚠️ 안내사항</h3>
              <ul>
                <li>챗봇 답변은 민원 안내를 돕기 위한 참고용입니다.</li>
                <li>정확한 최신 정보는 담당 부서 또는 공식 홈페이지를 확인해주세요.</li>
              </ul>
            </section>

            <button
              type="button"
              className="guide-confirm-button"
              onClick={() => setShowGuide(false)}
            >
              확인했어요
            </button>
          </div>
        </div>
      )}

      {/* 음성 입력, 음성 출력, 글자 크기 조절 영역 */}
      <div className="accessibility-bar">
        <div className="voice-accessibility-controls">
          <button
            type="button"
            className={isListening ? "voice-button active" : "voice-button"}
            onClick={handleStartStt}
            disabled={isLoading}
          >
            {isListening ? "🎙️ 녹음 중..." : "🎤 음성 입력"}
          </button>

          <button
            type="button"
            className={isTtsOn ? "voice-button active" : "voice-button"}
            onClick={handleToggleTts}
          >
            {isTtsOn ? "🔊 답변 음성 ON" : "🔇 답변 음성 OFF"}
          </button>

          <button type="button" className="voice-button" onClick={handleReplayTts}>
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

      {/* 메인 화면 영역 */}
      <main className="main-layout">
        <section className="left-section">
          <MascotCard />
        </section>

        <section className="chat-section">
          <ChatWindow
            messages={messages}
            isLoading={isLoading}
            similarityScore={similarityScore}
          />

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