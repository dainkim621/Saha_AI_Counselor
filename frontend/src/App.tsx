import { useEffect, useRef, useState } from "react";
import "./App.css";

import Header from "./components/Header";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";

// FastAPI 백엔드 서버 주소
//const BACKEND_URL = 'https://snack-sanded-passover.ngrok-free.dev'; // 상대 경로로 변경하여 프록시 설정 사용
const BACKEND_URL = 'http://localhost:8000';  // 다인 임시로 로컬 쓴거

// 채팅 메시지 데이터 구조
export type Message = {
  role: "user" | "assistant";
  content: string;
  questionTitle?: string;
  files?: { file_name: string; file_url: string }[];
  similarityScore?: number;
};

type SavedChat = {
  id: number;
  title: string;
  messages: Message[];
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
  const [messages, setMessages] = useState<Message[]>([]);
  
  // 현재 접속 중에만 유지되는 상담 내역
  const [savedChats, setSavedChats] = useState<SavedChat[]>([]);
  
  // 상담 내역 접기/펼치기
  const [historyOpen, setHistoryOpen] = useState(true)
  
  // PC 왼쪽 사이드바 접기/펼치기
  const [leftSidebarOpen, setLeftSidebarOpen] = useState(true);
  // FAQ 접기/펼치기 상태
  const [faqOpen, setFaqOpen] = useState(false);

  // PC 현재 채팅 질문 목록 접기/펼치기
  const [, setQuestionListOpen] = useState(false);

  // 현재 채팅 질문 목록에서 선택된 질문 번호
  const [activeQuestionIndex, setActiveQuestionIndex] = useState(0);
  // 모바일 질문 이동 목록 접기/펼치기
  const [mobileQuestionListOpen, setMobileQuestionListOpen] = useState(false);
  
  // 현재 상담 및 다음 상담 식별자
  const activeChatIdRef = useRef(0);
  const nextChatIdRef = useRef(1);

  // AI가 생성한 현재 상담 제목
  const activeChatTitleRef = useRef<string>("");
  
  // 질문이 입력되면 상담 내역에 즉시 등록하고
  // 이후 AI 답변까지 같은 상담 내역에 갱신
  useEffect(() => {
    const firstQuestion = messages.find(
      (message) => message.role === "user"
    )?.content;

    // 아직 질문하지 않은 빈 채팅은 저장하지 않음
    if (!firstQuestion) return;

    const chatId = activeChatIdRef.current;

    const title =
      activeChatTitleRef.current ||
      firstQuestion.slice(0, 11) +
        (firstQuestion.length > 11 ? "…" : "");

    const currentChat: SavedChat = {
      id: chatId,
      title,
      messages: messages.map((message) => ({
        ...message,
        files: message.files?.map((file) => ({ ...file })),
      })),
    };

    setSavedChats((prev) => {
      const exists = prev.some(
        (chat) => chat.id === chatId
      );

      // 이미 등록된 상담이면 메시지만 갱신
      if (exists) {
        return prev.map((chat) =>
          chat.id === chatId ? currentChat : chat
        );
      }

      // 처음 질문한 상담이면 목록 맨 아래에 추가
      return [currentChat, ...prev];
    });
  }, [messages]);
  
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
  const [similarityScore, setSimilarityScore] =
    useState<number | null>(null);

  // 이용 가이드 모달 표시 여부
  const [showGuide, setShowGuide] = useState(false);


  // 이용 가이드 선택 탭
  const [showPrivacy, setShowPrivacy] = useState(false);
  const [guideTab, setGuideTab] = useState<"questions" | "features">("questions");

  /*
   * QuickMenu에 표시할 질문 목록
   *
   * 처음에는 기본 FAQ가 표시되고,
   * 질문 기록이 있으면 최근 7일 집계 결과로 변경된다.
   */
  // 백엔드에서 받아온 자주 묻는 질문 Top 5
  const [weeklyQuestions, setWeeklyQuestions] = useState<string[]>([]);

  // 마지막으로 읽은 assistant 메시지 인덱스 저장
  const lastSpokenIndexRef = useRef<number>(-1);

  // STT 녹음 객체 저장
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // 마이크 스트림 저장
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // 녹음된 음성 조각 저장
  const audioChunksRef = useRef<Blob[]>([]);

  // 페이지가 처음 열릴 때 백엔드에서 자주 묻는 질문 Top 5 조회
  // 페이지가 열리면 자동으로 GET http://localhost:8000/frequent-questions가 호출됨.
  useEffect(() => {
    const fetchFrequentQuestions = async () => {
      try {
        const response = await fetch(`${BACKEND_URL}/frequent-questions`);

        if (!response.ok) {
          throw new Error("자주 묻는 질문 조회 실패");
        }

        const data = await response.json();

        // 백엔드 응답에서 질문을 추출하고 불필요한 따옴표 제거
        const questions: string[] = data.map(
          (item: { question: string; count: number }) =>
            item.question
              .trim()
              .replace(/^['"“”‘’]+|['"“”‘’]+$/g, "")
              .trim()
          );

          // 띄어쓰기만 다른 동일 질문은 한 번만 표시
          const uniqueQuestions = questions.filter(
            (question: string, index: number) =>
              questions.findIndex(
                (other: string) =>
                  other.replace(/\s+/g, "").toLowerCase() ===
                  question.replace(/\s+/g, "").toLowerCase()
              ) === index
          );

          setWeeklyQuestions(uniqueQuestions);
      } catch (error) {
        console.error("자주 묻는 질문 조회 오류:", error);
        setWeeklyQuestions([]);
      }
    };

    fetchFrequentQuestions();
  }, []);
  
  // 브라우저 뒤로 가기 캐시에서 복원되는 경우 상담 내용 초기화
  useEffect(() => {
    const resetRestoredPage = (event: PageTransitionEvent) => {
      if (!event.persisted) return;

      // 임시 상담 내역 초기화
      setSavedChats([]);
      setHistoryOpen(false);

      // 현재 채팅 초기화
      setMessages([]);

      setInput("");
      setSimilarityScore(null);
      setActiveQuestionIndex(0);

      // 상담 식별자 초기화
      activeChatIdRef.current = 0;
      nextChatIdRef.current = 1;
      lastSpokenIndexRef.current = 0;
      activeChatTitleRef.current = "";

      window.speechSynthesis?.cancel();
    };

    window.addEventListener("pageshow", resetRestoredPage);

    return () => {
      window.removeEventListener("pageshow", resetRestoredPage);
    };
  }, []);

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
    // 브라우저가 음성 합성 기능을 지원하지 않으면 종료
    if (!("speechSynthesis" in window)) return;

    // 읽을 내용이 없으면 종료
    if (!text.trim()) return;

    // 기존에 재생 중인 음성 중지
    window.speechSynthesis.cancel();

    // Markdown 기호 등을 제거한 텍스트로 음성 생성
    const utterance = new SpeechSynthesisUtterance(
      cleanTextForTTS(text)
    );

    utterance.lang = "ko-KR";
    utterance.rate = 1;
    utterance.pitch = 1;
    utterance.volume = 1;

    window.speechSynthesis.speak(utterance);
  };

  // TTS가 켜져 있을 때 assistant 답변이 완성되면 자동으로 읽기
  useEffect(() => {
    // TTS가 꺼지면 재생 중인 음성도 중지
    if (!isTtsOn) {
      window.speechSynthesis?.cancel();
      return;
    }

    // 답변 생성 중에는 아직 읽지 않음
    if (isLoading) return;

    // 메시지가 없으면 종료
    if (messages.length === 0) return;

    const lastIndex = messages.length - 1;
    const lastMessage = messages[lastIndex];

    // 마지막 메시지가 assistant 답변이 아니면 종료
    if (lastMessage.role !== "assistant") return;

    // 답변 내용이 비어 있으면 종료
    if (!lastMessage.content.trim()) return;

    // 이미 읽었던 메시지이면 다시 자동 재생하지 않음
    if (lastSpokenIndexRef.current === lastIndex) return;

    lastSpokenIndexRef.current = lastIndex;
    speakText(lastMessage.content);
  }, [messages, isTtsOn, isLoading]);

  // 마이크 사용 종료 처리
  const stopMicrophone = () => {
    // 사용 중인 모든 마이크 트랙 종료
    mediaStreamRef.current?.getTracks().forEach((track) => {
      track.stop();
      console.log("마이크 트랙 종료:", track.readyState);
    });

    // 저장된 마이크 관련 객체 초기화
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
  };

  // 음성 입력 시작/종료 처리
  const handleStartStt = async () => {
    // 챗봇 답변 생성 중에는 음성 입력 차단
    if (isLoading) return;

    // 이미 녹음 중이면 녹음 종료
    if (isListening) {
      mediaRecorderRef.current?.stop();
      return;
    }

    try {
      // 브라우저에 마이크 사용 권한 요청
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });

      mediaStreamRef.current = stream;

      // 이전 녹음 데이터 초기화
      audioChunksRef.current = [];

      // 마이크 스트림을 사용하는 MediaRecorder 생성
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;

      // 녹음된 음성 데이터가 만들어질 때마다 배열에 저장
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // 녹음이 종료되었을 때 실행
      mediaRecorder.onstop = async () => {
        setIsListening(false);
        stopMicrophone();

        console.log("마이크 종료됨");

        // 녹음 조각을 하나의 webm 파일로 합치기
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/webm",
        });

        // 백엔드에 전송할 FormData 생성
        const formData = new FormData();
        formData.append("audio", audioBlob, "voice.webm");

        try {
          // STT 백엔드 API에 음성 파일 전송
          const response = await fetch(`${BACKEND_URL}/stt`, {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            throw new Error("STT 서버 응답 오류");
          }

          const data = await response.json();
          const transcript = data.text?.trim();

          // 인식된 텍스트가 없으면 종료
          if (!transcript) return;

          // 음성 인식 결과를 입력창에 표시
          setInput(transcript);

          // 음성 인식 결과를 사용자에게 다시 읽어줌
          speakText(transcript);
        } catch (error) {
          console.error("음성 인식 오류:", error);
          speakText("음성 인식 중 오류가 발생했습니다.");
        } finally {
          // 녹음 관련 임시 데이터 초기화
          mediaRecorderRef.current = null;
          audioChunksRef.current = [];
        }
      };

      // 녹음 상태 표시
      setIsListening(true);

      // 실제 녹음 시작
      mediaRecorder.start();

      // 최대 10초까지만 자동 녹음
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

      // TTS를 끄는 경우 현재 재생 중인 음성도 중지
      if (!next && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }

      return next;
    });
  };

  // 마지막 assistant 답변 다시 듣기
  const handleReplayTts = () => {
    // 최신 메시지부터 거꾸로 확인하여 마지막 assistant 답변 찾기
    const lastAssistantMessage = [...messages]
      .reverse()
      .find((message) => message.role === "assistant");

    if (!lastAssistantMessage) return;

    speakText(lastAssistantMessage.content);
  };

  // 음성 기능을 추후 다시 사용할 수 있도록 참조 유지
  void handleStartStt;
  void handleToggleTts;
  void handleReplayTts;

  // 사용자 질문을 백엔드로 전송하고 스트리밍 답변 수신
  const sendMessage = async (question: string) => {
    // 질문 앞뒤 공백 제거
    const trimmedQuestion = question.trim();

    // 빈 질문은 전송하지 않음
    if (!trimmedQuestion) return;

    // 이미 답변 생성 중이면 중복 전송하지 않음
    if (isLoading) return;

    // 현재 상담의 첫 질문인지 확인
    const isFirstQuestion = !messages.some(
      (message) => message.role === "user"
    );

    // PC에서는 첫 질문부터 상담 내역을 보여줌
    if (
      isFirstQuestion &&
      window.matchMedia("(min-width: 769px)").matches
    ) {
      setHistoryOpen(true);
    }

    const userMessage: Message = {
      role: "user",
      content: trimmedQuestion,
    };

    // 초기 인사말 제외 후 이전 대화 내역 전송
    const history = messages
      .filter(
        (message) =>
          message.content !==
          "안녕하세요! 사하구 민원 상담을 도와드릴게요."
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

    // 입력창 초기화
    setInput("");

    // 이전 질문의 유사도 점수 초기화
    setSimilarityScore(null);

    // 답변 생성 상태로 변경
    setIsLoading(true);

    try {
      // AI 채팅 백엔드 API 호출
      const response = await fetch(`${BACKEND_URL}/ai-chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          'ngrok-skip-browser-warning': 'true'
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

      // 스트리밍 응답을 읽기 위한 객체
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");

      // 잘려서 들어오는 SSE 데이터를 임시 저장할 문자열
      let buffer = "";

      // 서버가 답변 전송을 완료했는지 여부
      let isDone = false;

      while (!isDone) {
        const { value, done } = await reader.read();

        // 스트림 자체가 종료되면 반복 종료
        if (done) break;

        // 서버에서 받은 바이트 데이터를 문자열로 변환
        buffer += decoder.decode(value, { stream: true });

        // SSE 이벤트는 빈 줄 두 개로 구분됨
        const events = buffer.split("\n\n");

        // 아직 완성되지 않은 마지막 데이터는 buffer에 유지
        buffer = events.pop() || "";

        for (const event of events) {
          // SSE 데이터 형식이 아니면 건너뜀
          if (!event.startsWith("data: ")) continue;

          const data = event.replace("data: ", "").trim();

          // 백엔드가 전송 완료 신호를 보낸 경우
          if (data === "[DONE]") {
            isDone = true;
            break;
          }

          // JSON 문자열을 객체로 변환
          const parsed = JSON.parse(data);

          // 첫 질문의 AI 요약 제목 저장
          // AI가 생성한 질문 제목 저장
          if (parsed.type === "title") {
            const title = String(parsed.content ?? "").trim();

            if (title) {
              // 현재 질문에 AI 제목 저장
              setMessages((prev) => {
                const updated = [...prev];

                for (let i = updated.length - 1; i >= 0; i--) {
                  if (updated[i].role === "user") {
                    updated[i] = {
                      ...updated[i],
                      questionTitle: title,
                    };
                    break;
                  }
                }

                return updated;
              });

              // 첫 질문의 제목은 기존 상담 내역 제목에도 사용
              if (isFirstQuestion) {
                activeChatTitleRef.current = title;

                const chatId = activeChatIdRef.current;

                setSavedChats((prev) =>
                  prev.map((chat) =>
                    chat.id === chatId
                      ? { ...chat, title }
                      : chat
                  )
                );
              }
            }
          }

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
                content:
                  updated[lastIndex].content + parsed.content,
              };

              return updated;
            });

            // 스트리밍 출력이 너무 빠르지 않도록 약간의 지연 적용
            await new Promise((resolve) =>
              setTimeout(resolve, 20)
            );
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

          // 백엔드에서 오류 데이터를 보낸 경우
          if (parsed.type === "error") {
            throw new Error(parsed.content);
          }
        }
      }
    } catch (error) {
      console.error("채팅 서버 연결 오류:", error);

      // 빈 assistant 메시지를 오류 안내 메시지로 교체
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
      // 성공 또는 실패 여부와 관계없이 로딩 종료
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

  // 새로운 상담 시작
  const handleNewChat = () => {
    if (isLoading || isListening) return;

    window.speechSynthesis?.cancel();

    // 기존 상담을 목록에 보관
    activeChatTitleRef.current = "";

    // 완전히 새로운 상담 ID 부여
    activeChatIdRef.current = nextChatIdRef.current++;

    // 이전 질문/답변 초기화
    setMessages([]);

    setInput("");
    setSimilarityScore(null);
    lastSpokenIndexRef.current = -1;
    setMobileQuestionListOpen(false);

    // Figma Frame 1: 새 채팅 후 최근 상담 목록 표시
    setHistoryOpen(true);
    setFaqOpen(false);
  };

  // 상담 내역에서 이전 상담 선택
  const handleRestoreChat = (selectedChat: SavedChat) => {
    if (isLoading || isListening) return;

    window.speechSynthesis?.cancel();

    // 선택한 상담을 현재 상담으로 복원
    activeChatIdRef.current = selectedChat.id;
    activeChatTitleRef.current = selectedChat.title;
    setMessages(selectedChat.messages);
    setActiveQuestionIndex(0);

    // 상담 전환 후 현재 채팅 질문 목록 펼치기
    setQuestionListOpen(true);

    // 모바일 질문 목록 팝업 닫기
    setMobileQuestionListOpen(false);

    // 입력창 초기화
    setInput("");

    // 해당 상담의 마지막 매칭도 복원
    const lastScore = [...selectedChat.messages]
      .reverse()
      .find(
        (message) =>
          message.role === "assistant" &&
          message.similarityScore !== undefined
      )?.similarityScore;

    setSimilarityScore(lastScore ?? null);

    // 복원한 답변을 자동 재생하지 않도록 설정
    lastSpokenIndexRef.current =
      selectedChat.messages.length - 1;
    setMobileQuestionListOpen(false);
  };
  
  // 현재 채팅에서 사용자 질문만 추출
  // 현재 채팅에서 사용자 질문과 AI 제목 추출
  const currentQuestions = messages
    .filter((message) => message.role === "user")
    .map((message) => {
      const content = message.content.replace(/\s+/g, " ").trim();

      return {
        content,
        title:
          message.questionTitle?.trim() ||
          (content.length > 24
            ? `${content.slice(0, 24)}…`
            : content),
      };
    });
    
    // 선택한 질문 위치로 이동
    const jumpToQuestion = (questionIndex: number) => {
      const chatWindow =
        document.querySelector<HTMLElement>(".chat-window");

      const questionRows =
        chatWindow?.querySelectorAll<HTMLElement>(".user-row");

      const target = questionRows?.[questionIndex];

      if (!chatWindow || !target) return;
      // 클릭한 질문을 현재 선택된 항목으로 표시
      setActiveQuestionIndex(questionIndex);

      const offset =
        target.getBoundingClientRect().top -
        chatWindow.getBoundingClientRect().top;

      chatWindow.scrollTo({
        top: Math.max(
          0,
          chatWindow.scrollTop + offset - 12
        ),
        behavior: "smooth",
      });

      setMobileQuestionListOpen(false);
    };

  // 현재 채팅에 사용자 질문이 있는지 확인
  const hasUserMessage = messages.some(
    (message) => message.role === "user"
  );

  return (
    <div className={`app ${fontModes[fontLevel]}`}>
      
      {/* 상단 헤더 및 오른쪽 도구 버튼 */}
      <div className="header-top-row">
        <Header onGuideClick={() => setShowGuide(true)} />

        <div className="header-actions">
          {/* 이용 가이드 */}
          <button
            type="button"
            className="guide-toolbar-button"
            onClick={() => setShowGuide(true)}
            title="이용 가이드"
            aria-label="이용 가이드 열기"
          >
            ?
          </button>

      {/* 글자 크기 조절 */}
      <div className="font-controls">
        <span>글자 크기</span>

        <button
          type="button"
          onClick={decreaseFont}
          aria-label="글자 크기 줄이기"
        >
          －
        </button>

        <div className="font-label">
          {fontLabels[fontLevel]}
        </div>

        <button
          type="button"
          onClick={increaseFont}
          aria-label="글자 크기 키우기"
        >
          ＋
        </button>
      </div>
    </div>
  </div>
      
      {/* 개인정보 보호 상세 안내 */}
      {showPrivacy && (
        <div
          className="guide-overlay"
          onClick={() => setShowPrivacy(false)}
        >
          <div
            className="guide-modal privacy-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="privacy-modal-title"
            onClick={(event) => event.stopPropagation()}
          >
            {/* 헤더 */}
            <div className="privacy-modal-header">
              <h2 id="privacy-modal-title">개인정보 보호 안내</h2>

              <button
                type="button"
                className="privacy-modal-close"
                onClick={() => setShowPrivacy(false)}
                aria-label="닫기"
              >
                ✕
              </button>
            </div>

            {/* 안내 본문 */}
            <div className="privacy-modal-body">
              <div className="privacy-info-item">
                <div className="privacy-info-icon">
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z" />
                    <path d="M12 8v5" />
                    <path d="M12 17h.01" />
                  </svg>
                </div>

                <div className="privacy-info-text">
                  <h3>개인정보 입력 주의</h3>
                  <p>
                    개인정보 보호를 위해 주민등록번호, 전화번호, 상세 주소 등
                    개인을 식별할 수 있는 정보는 입력하지 마세요.
                  </p>
                </div>
              </div>

              <div className="privacy-divider" />

              <div className="privacy-info-item">
                <div className="privacy-info-icon">
                  <svg
                    width="20"
                    height="20"
                    viewBox="0 0 24 24"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="1.8"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    aria-hidden="true"
                  >
                    <rect x="5" y="4" width="14" height="18" rx="2" />
                    <rect x="9" y="2" width="6" height="4" rx="1" />
                    <path d="M9 11h.01M12 11h4M9 15h.01M12 15h4" />
                  </svg>
                </div>

                <div className="privacy-info-text">
                  <h3>상담 내용 처리</h3>
                  <p>
                    입력한 질문은 상담 서비스 제공 및 품질 개선을 위해
                    처리될 수 있습니다.
                  </p>
                </div>
              </div>
            </div>

            {/* 확인 버튼 */}
            <button
              type="button"
              className="privacy-confirm-button"
              onClick={() => setShowPrivacy(false)}
            >
              확인
            </button>
          </div>
        </div>
      )}

      {/* 이용 가이드 모달 */}
      {showGuide && (
        <div
          className="guide-overlay"
          onClick={() => setShowGuide(false)}
        >
          <div
            className="guide-modal figma-guide-modal"
            role="dialog"
            aria-modal="true"
            aria-labelledby="figma-guide-title"
            onClick={(event) => event.stopPropagation()}
          >
            {/* 모달 헤더 */}
            <div className="figma-guide-header">
              <h2 id="figma-guide-title">
                AI 상담사 이용 안내
              </h2>

              <button
                type="button"
                className="figma-guide-close"
                onClick={() => setShowGuide(false)}
                aria-label="이용 가이드 닫기"
              >
                ✕
              </button>
            </div>

            {/* 질문 예시 / 사용 가능한 기능 탭 */}
            <div className="figma-guide-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={guideTab === "questions"}
                className={`figma-guide-tab ${
                  guideTab === "questions" ? "active" : ""
                }`}
                onClick={() => setGuideTab("questions")}
              >
                질문 예시
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={guideTab === "features"}
                className={`figma-guide-tab ${
                  guideTab === "features" ? "active" : ""
                }`}
                onClick={() => setGuideTab("features")}
              >
                사용 가능한 기능
              </button>
            </div>

            {/* 모달 본문 */}
            <div className="figma-guide-body">
              {guideTab === "questions" ? (
                <div className="figma-guide-question-list">
                  {[
                    "전입신고는 어떻게 하나요?",
                    "가족관계 증명서 발급은 어떻게 해?",
                    "대형 폐기물 배출 방법 알려줘",
                    "여권 발급 준비물이 뭐야?",
                  ].map((question, index) => (
                    <div
                      className="figma-guide-question"
                      key={index}
                    >
                      <span className="figma-guide-number">
                        {String(index + 1).padStart(2, "0")}
                      </span>
                      <span>{question}</span>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="figma-guide-feature-list">
                  {[
                    {
                      icon: "plus",
                      title: "새 채팅",
                      description: "새 상담 시작",
                    },
                    {
                      icon: "history",
                      title: "최근 문의",
                      description: "이전 상담 확인",
                    },
                    {
                      icon: "list",
                      title: "자주 찾는 민원",
                      description: "인기 질문 TOP 5",
                    },
                    {
                      icon: "ordered",
                      title: "현재 채팅 질문 목록",
                      description: "질문·답변 바로 이동",
                    },
                    {
                      icon: "font",
                      title: "글자 크기 조절",
                      description: "5단계 크기 조절",
                    },
                    {
                      icon: "download",
                      title: "첨부파일 다운로드",
                      description: "민원 서식 다운로드",
                    },
                  ].map((feature) => (
                    <div
                      className="figma-guide-feature"
                      key={feature.title}
                    >
                      <div className="figma-guide-feature-icon">
                        <svg
                          width="20"
                          height="20"
                          viewBox="0 0 24 24"
                          fill="none"
                          stroke="#525252"
                          strokeWidth="1.8"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          aria-hidden="true"
                        >
                          {feature.icon === "plus" && (
                            <>
                              <path d="M20 11.5a8.4 8.4 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.4 8.4 0 0 1-3.8-.9L2 21l1.9-5.7a8.4 8.4 0 0 1-.9-3.8 8.5 8.5 0 0 1 8.5-8.5" />
                              <path d="M18 2v8M14 6h8" />
                            </>
                          )}

                          {feature.icon === "history" && (
                            <>
                              <path d="M3 12a9 9 0 1 0 3-6.7L3 8" />
                              <path d="M3 3v5h5M12 7v5l3 2" />
                            </>
                          )}

                          {feature.icon === "list" && (
                            <>
                              <path d="M8 6h13M8 12h13M8 18h13" />
                              <path d="M3 6h.01M3 12h.01M3 18h.01" />
                            </>
                          )}

                          {feature.icon === "ordered" && (
                            <>
                              <path d="M10 6h11M10 12h11M10 18h11" />
                              <path d="M4 5h1v4M3 9h3M3 14c0-1 3-1 3 0s-3 2-3 4h3" />
                            </>
                          )}

                          {feature.icon === "font" && (
                            <>
                              <path d="m3 18 5-12 5 12M5 14h6" />
                              <path d="m15 18 3.5-9 3.5 9M16.5 15h4" />
                            </>
                          )}

                          {feature.icon === "download" && (
                            <>
                              <path d="M12 3v12m-5-5 5 5 5-5" />
                              <path d="M4 17v3h16v-3" />
                            </>
                          )}
                        </svg>
                      </div>

                      <div className="figma-guide-feature-text">
                        <span className="figma-guide-feature-title">
                          {feature.title}
                        </span>
                        <span className="figma-guide-feature-description">
                          {feature.description}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* 하단 안내 */}
            <p className="figma-guide-notice">
              AI 답변은 참고용입니다. 정확한 정보는 담당 부서 또는
              공식 홈페이지에서 확인해 주세요.
            </p>
          </div>
        </div>
      )}
      {/* 음성 입력, 음성 출력, 글자 크기 조절 영역 */}
      <div className="accessibility-bar">
        <div className="voice-accessibility-controls">
         {/* <button
            type="button"
            className={
              isListening
                ? "voice-button active"
                : "voice-button"
            }
            onClick={handleStartStt}
            disabled={isLoading}
          >
            {isListening ? "🎙️ 녹음 중..." : "🎤 음성 입력"}
          </button>

          <button
            type="button"
            className={
              isTtsOn
                ? "voice-button active"
                : "voice-button"
            }
            onClick={handleToggleTts}
          >
            {isTtsOn
              ? "🔊 답변 음성 ON"
              : "🔇 답변 음성 OFF"}
          </button>

          <button
            type="button"
            className="voice-button"
            onClick={handleReplayTts}
          >
            ↻ 다시 듣기
          </button>*/}

          {/* 개인정보 보호 안내 */}
          <div className="privacy-warning" role="note">
            <span className="privacy-warning-text">
              주민등록번호, 연락처 등 개인정보는 입력하지 마세요.
            </span>

            <button
              type="button"
              className="privacy-warning-detail"
              onClick={() => setShowPrivacy(true)}
            >
              상세보기
            </button>
          </div>
        </div>
      </div>
      
      {/* 메인 화면 영역 */}
      <main className="main-layout">
        {/* 왼쪽 사이드바 */}
        <aside
          className={`left-section ${leftSidebarOpen ? "" : "collapsed"}`}
        >
        <div className="figma-pc-sidebar">
          <div className="figma-sidebar-top">
            <h1 className="figma-sidebar-title">
              사하구 AI 상담사
            </h1>

            <button
              type="button"
              className="figma-sidebar-toggle"
              onClick={() => setLeftSidebarOpen((prev) => !prev)}
              aria-label={leftSidebarOpen ? "왼쪽 사이드바 접기" : "왼쪽 사이드바 펼치기"}
              aria-expanded={leftSidebarOpen}
              title={leftSidebarOpen ? "사이드바 접기" : "사이드바 펼치기"}
            >
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="1.8"
                strokeLinecap="round"
                strokeLinejoin="round"
                aria-hidden="true"
              >
                <path d="M4 6h16" />
                <path d="M4 12h16" />
                <path d="M4 18h16" />
              </svg>
            </button>
          </div>

            

            <button
              type="button"
              className="figma-new-chat-button"
              onClick={handleNewChat}
              disabled={isLoading || isListening}
            >
              + 새 채팅
            </button>

            <div className="figma-sidebar-sections">
              {/* 최근 문의 */}
              <section className="figma-recent-section">
                <button
                  className="figma-accordion-header"
                  onClick={() => {
                    setHistoryOpen((prev) => !prev);
                    setFaqOpen(false);
                  }}
                  aria-expanded={historyOpen}
                >
                  최근 문의
                  <span className={`figma-accordion-arrow ${historyOpen ? "open" : ""}`} />
                </button>

                {historyOpen && (
                  <div className="figma-recent-list">
                    {savedChats.length === 0 ? (
                      <p className="figma-history-empty">
                        아직 상담 내역이 없습니다.
                      </p>
                    ) : (
                      savedChats.map((chat) => (
                        <button
                          key={chat.id}
                          className={`figma-recent-item ${
                            chat.id === activeChatIdRef.current ? "active" : ""
                          }`}
                          onClick={() => handleRestoreChat(chat)}
                        >
                          {chat.title}
                        </button>
                      ))
                    )}
                  </div>
                )}
              </section>

              {/* 자주 찾는 민원 */}
              <section className="figma-faq-section">
                <button
                  type="button"
                  className="figma-accordion-header"
                  onClick={() => {
                    setFaqOpen((prev) => !prev);
                    setHistoryOpen(false);
                  }}
                  aria-expanded={faqOpen}
                >
                  <span>자주 찾는 민원</span>
                  <span
                    className={`figma-accordion-arrow ${
                      faqOpen ? "open" : ""
                    }`}
                    aria-hidden="true"
                  />
                </button>

                {faqOpen && (
                  <div className="figma-faq-list">
                    {weeklyQuestions.length === 0 ? (
                      <p className="figma-history-empty">
                        표시할 질문이 없습니다.
                      </p>
                    ) : (
                      weeklyQuestions.map((question, index) => (
                        <button
                          key={`${question}-${index}`}
                          type="button"
                          className="figma-faq-item"
                          onClick={() => sendMessage(question)}
                          disabled={isLoading}
                        >
                          {question}
                        </button>
                      ))
                    )}
                  </div>
                )}
              </section>
            </div>
          </div>
        </aside>

        {/* Figma MainArea */}
        <section className="chat-section">
          {/* 상단 헤더 */}
          <header className="figma-pc-toolbar">
            {!leftSidebarOpen && (
              <button
                type="button"
                className="figma-sidebar-toggle"
                onClick={() => setLeftSidebarOpen(true)}
                aria-label="왼쪽 사이드바 펼치기"
                title="사이드바 펼치기"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M4 6h16" />
                  <path d="M4 12h16" />
                  <path d="M4 18h16" />
                </svg>
              </button>
            )}
            
            <div className="figma-toolbar-privacy">
              <span>
                주민등록번호, 연락처 등 개인정보는 입력하지 마세요.
              </span>

              <button
                type="button"
                className="figma-privacy-detail"
                onClick={() => setShowPrivacy(true)}
              >
                상세보기
              </button>
            </div>

            <div className="figma-toolbar-actions">
              <span className="figma-font-caption">
                글자 크기
              </span>

              <div className="figma-font-control">
                <button
                  type="button"
                  onClick={decreaseFont}
                  disabled={fontLevel === 0}
                  aria-label="글자 크기 줄이기"
                >
                  A-
                </button>

                <span>{fontLabels[fontLevel]}</span>

                <button
                  type="button"
                  onClick={increaseFont}
                  disabled={fontLevel === 4}
                  aria-label="글자 크기 키우기"
                >
                  A+
                </button>
              </div>

              <button
                type="button"
                className="figma-guide-button"
                onClick={() => setShowGuide(true)}
                aria-label="이용 가이드 열기"
                title="이용 가이드"
              >
                ?
              </button>
            </div>
          </header>

          {/* 모바일 현재 채팅 질문 목록 버튼 */}
          {hasUserMessage && (
            <div className="current-questions-mobile">
              <button
                type="button"
                className="current-questions-mobile-button"
                onClick={() => setMobileQuestionListOpen(true)}
                aria-label="현재 채팅 질문 목록 열기"
                title="현재 질문 목록"
              >
                <svg
                  width="20"
                  height="20"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.8"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <path d="M8 6h13" />
                  <path d="M8 12h13" />
                  <path d="M8 18h13" />
                  <path d="M3 6h.01" />
                  <path d="M3 12h.01" />
                  <path d="M3 18h.01" />
                </svg>
              </button>
            </div>
          )}

          {/* 환영 화면 / 상담 화면 */}
          <div
            className={`figma-chat-layout ${
              hasUserMessage ? "has-chat" : "is-welcome"
            }`}
          >
            <div className="figma-chat-main">
              {!hasUserMessage ? (
                <div className="figma-welcome">
                  <div className="figma-welcome-content">
                    <img
                      src="/src/assets/gouni-first.png"
                      alt="사하구 AI 민원 상담사 고우니"
                      className="figma-welcome-mascot"
                    />
                    <h2>어떤 민원 정보를 찾으시나요?</h2>

                    <p>
                      필요한 민원 정보를 빠르게 확인해 보세요.
                    </p>

                    <div className="figma-welcome-input">
                      <ChatInput
                        input={input}
                        setInput={setInput}
                        onSend={sendMessage}
                        isLoading={isLoading}
                      />
                    </div>
                    {/* 안내 가능한 민원 분야 */}
                    <div className="figma-welcome-categories">
                      <h3>안내 가능한 민원 분야</h3>

                      <div className="figma-welcome-category-grid">
                        <div className="figma-welcome-category">
                          <strong>주민등록·가족관계</strong>
                          <span>신고 절차 및 증명서 발급 안내</span>
                        </div>

                        <div className="figma-welcome-category">
                          <strong>여권·민원서식</strong>
                          <span>구비서류와 발급 절차 안내</span>
                        </div>

                        <div className="figma-welcome-category">
                          <strong>환경·폐기물</strong>
                          <span>생활폐기물 배출 및 신고 안내</span>
                        </div>

                        <div className="figma-welcome-category">
                          <strong>복지·생활지원</strong>
                          <span>복지 혜택 및 지원 제도 안내</span>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              ) : (
                <>
                  <ChatWindow
                    messages={messages}
                    isLoading={isLoading}
                    similarityScore={similarityScore}
                  />

                  <div className="figma-chat-input-bottom">
                    <ChatInput
                      input={input}
                      setInput={setInput}
                      onSend={sendMessage}
                      isLoading={isLoading}
                    />
                  </div>
                </>
              )}
            </div>

            {/* 현재 채팅 질문 목록 */}
            {hasUserMessage && (
              <aside className="right-question-panel">
                <h2 className="right-question-heading">
                  현재 채팅 질문 목록
                </h2>

                <div className="right-question-list">
                  {currentQuestions.map((question, index) => (
                    <button
                      key={index}
                      type="button"
                      className={`right-question-item ${
                        index === activeQuestionIndex ? "active" : ""
                      }`}
                      title={question.content}
                      disabled={isLoading}
                      onClick={() => jumpToQuestion(index)}
                    >
                      <span className="right-question-number">
                        {String(index + 1).padStart(2, "0")}
                      </span>

                      <span className="right-question-text">
                        {question.title}
                      </span>
                    </button>
                  ))}
                </div>
              </aside>
            )}
          </div>
        </section>
      </main>

      
      {/* 모바일 질문 목록 팝업 */}
      {mobileQuestionListOpen && (
        <div
          className="mobile-questions-backdrop"
          onClick={() => setMobileQuestionListOpen(false)}
        >
          <div
            className="mobile-questions-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="mobile-questions-heading"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="mobile-questions-header">
              <h2 id="mobile-questions-heading">
                현재 채팅 질문
              </h2>

              <button
                type="button"
                className="mobile-questions-close"
                onClick={() => setMobileQuestionListOpen(false)}
                aria-label="질문 목록 닫기"
              >
                ✕
              </button>
            </div>

            <div className="mobile-questions-list">
              {currentQuestions.length === 0 ? (
                <p className="mobile-questions-empty">
                  아직 입력한 질문이 없습니다.
                </p>
              ) : (
                currentQuestions.map((question, index) => (
                  <button
                    key={index}
                    type="button"
                    className="current-question-item"
                    title={question.content}
                    disabled={isLoading}
                    onClick={() => jumpToQuestion(index)}
                  >
                    {index + 1}. {question.title}
                  </button>
                ))
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
}

export default App;