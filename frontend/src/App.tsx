import { useEffect, useRef, useState } from "react";
import "./App.css";

import Header from "./components/Header";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import QuickMenu from "./components/QuickMenu";

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
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "assistant",
      content: "안녕하세요! 사하구 민원 상담을 도와드릴게요.",
    },
  ]);
  
  // 현재 접속 중에만 유지되는 상담 내역
  const [savedChats, setSavedChats] = useState<SavedChat[]>([]);
  
  // 상담 내역 접기/펼치기
  const [historyOpen, setHistoryOpen] = useState(false);
  // FAQ 접기/펼치기 상태
  const [faqOpen, setFaqOpen] = useState(false);

  // PC 현재 채팅 질문 목록 접기/펼치기
  const [questionListOpen, setQuestionListOpen] = useState(false);
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
      return [...prev, currentChat];
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
      setMessages([
        {
          role: "assistant",
          content: "안녕하세요! 사하구 민원 상담을 도와드릴게요.",
        },
      ]);

      setInput("");
      setSimilarityScore(null);

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
    setMessages([
      {
        role: "assistant",
        content: "안녕하세요! 사하구 민원 상담을 도와드릴게요.",
      },
    ]);

    setInput("");
    setSimilarityScore(null);
    lastSpokenIndexRef.current = 0;
    setMobileQuestionListOpen(false);
  };

  // 상담 내역에서 이전 상담 선택
  const handleRestoreChat = (selectedChat: SavedChat) => {
    if (isLoading || isListening) return;

    window.speechSynthesis?.cancel();

    // 선택한 상담을 현재 상담으로 복원
    activeChatIdRef.current = selectedChat.id;
    activeChatTitleRef.current = selectedChat.title;
    setMessages(selectedChat.messages);

    // 상담 전환 후 현재 채팅 질문 목록 펼치기
    setQuestionListOpen(true);

    // 상담 내역 메뉴 닫기
    setHistoryOpen(false);

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
              <path d="M12 7v14" />
              <path d="M3 18V5a2 2 0 0 1 2-2h3a4 4 0 0 1 4 4" />
              <path d="M12 7a4 4 0 0 1 4-4h3a2 2 0 0 1 2 2v13" />
              <path d="M3 18a1 1 0 0 0 1 1h4a4 4 0 0 1 4 2 4 4 0 0 1 4-2h4a1 1 0 0 0 1-1" />
            </svg>
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

      {/* 이용 가이드 모달 */}
      {showGuide && (
        <div
          className="guide-overlay"
          onClick={() => setShowGuide(false)}
        >
          <div
            className="guide-modal"
            onClick={(event) => event.stopPropagation()}
          >
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
              고우니 챗봇은 사하구 민원 정보를 쉽게 안내해주는
              AI 상담사입니다.
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
                <li>새 채팅으로 새로운 상담 시작하기</li>
                <li>자주 묻는 질문 이용하기</li>
                <li>이전 상담 내역 확인하기</li>
                <li>
                  이전 질문·답변으로 이동하기 (🖥️ PC: 현재 채팅 질문 / 📱 모바일: 우측 목록 아이콘)
                </li>
                <li>글자 크기 조절하기</li>
                <li>관련 첨부파일 다운로드하기</li>
              </ul>
            </section>

            <section className="guide-section">
              <h3>⚠️ 안내사항</h3>

              <ul>
                <li>
                  챗봇 답변은 민원 안내를 돕기 위한 참고용입니다.
                </li>
                <li>
                  정확한 최신 정보는 담당 부서 또는 공식 홈페이지를
                  확인해주세요.
                </li>
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
            <span className="privacy-warning-icon" aria-hidden="true">
              🔒
            </span>
            <span className="privacy-warning-text">
              개인정보 보호를 위해 주민등록번호, 연락처, 주소 등은
              입력하지 마세요.
            </span>
          </div>
        </div>
      </div>

      {/* 메인 화면 영역 */}
      <main className="main-layout">
        <section className="left-section">

          {/* 새로운 상담을 시작하는 버튼 */}
          <button
            type="button"
            className="new-chat-button"
            onClick={handleNewChat}
            disabled={isLoading || isListening}
          > 
            {/* 새 채팅 아이콘 */}
            <span className="new-chat-icon" aria-hidden="true">
              ＋
            </span>

            {/* 버튼 이름 */}
            <span className="new-chat-text">
              새 채팅
            </span> 
          </button>

          {/* 자주 묻는 질문 */}
          <QuickMenu
            /*
             * App.tsx에서 계산한 최근 7일 질문 목록을
             * QuickMenu 컴포넌트에 전달한다.
             */
            questions={weeklyQuestions}
            // FAQ 버튼을 누르면 해당 질문을 바로 챗봇에 전송
            onSelect={sendMessage}
            // 답변 생성 중에는 FAQ 버튼 비활성화
            disabled={isLoading}
            isOpen={faqOpen}
            onToggle={() => {
              setFaqOpen((prev) => !prev);
              // 모바일에서만 상담 내역 닫기
              if (window.matchMedia("(max-width: 768px)").matches) {
                setHistoryOpen(false);
              }
            }}
          />
          
          {/* 현재 채팅 질문 - PC 사이드바 */}
          <div className="current-questions-menu">
            <button
              type="button"
              className="current-questions-toggle"
              aria-expanded={questionListOpen}
              aria-controls="current-questions-list"
              onClick={() => {
                setQuestionListOpen((prev) => !prev);
                setFaqOpen(false);
                setHistoryOpen(false);
              }}
            >
              <svg
                width="18"
                height="18"
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

              <span className="current-questions-title">
                현재 채팅 질문
              </span>
              
              <span
                className="current-questions-arrow"
                aria-hidden="true"
              />
            </button>

            {questionListOpen && (
              <div
                id="current-questions-list"
                className="current-questions-list"
              >
                {currentQuestions.length === 0 ? (
                  <p className="current-questions-empty">
                    질문을 입력하면 여기에 표시됩니다.
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
            )}
          </div>

          {/* 상담 내역 - 현재 접속 중에만 임시 보관 */}
          <div className="history-menu">
            <button
              type="button"
              className="history-toggle"
              onClick={() => {
                setHistoryOpen((prev) => !prev);
                // 모바일에서만 FAQ 닫기
                if (window.matchMedia("(max-width: 768px)").matches) {
                  setFaqOpen(false);
                }
              }}
              aria-expanded={historyOpen}
              aria-controls="saved-chat-history"
            >
      {/* 상담 내역 아이콘 */}
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <path d="M3 12a9 9 0 1 0 3-6.7" />
        <path d="M3 3v5h5" />
        <path d="M12 7v5l3 2" />
      </svg>

      <span className="history-title">
        상담 내역
      </span>

      <span
        className="history-arrow"
        aria-hidden="true"
      />
    </button>

    {historyOpen && (
      <div
        id="saved-chat-history"
        className="history-list"
      >
        {savedChats.length === 0 ? (
          <p className="history-empty">
            아직 이전 상담이 없습니다.
          </p>
        ) : (
          savedChats.map((chat) => (
            <button
              key={chat.id}
              type="button"
              className="history-item"
              onClick={() => handleRestoreChat(chat)}
              disabled={isLoading || isListening}
              title={chat.title}
            >
              {chat.title}
            </button>
          ))
        )}
      </div>
    )}
  </div>

        </section>

        <section className="chat-section">
          {/* 모바일 전용 질문 목록 아이콘 */}
          <div className="current-questions-mobile">
            <button
              type="button"
              className="current-questions-mobile-button"
              onClick={() => {
                setMobileQuestionListOpen(true);
                setFaqOpen(false);
                setHistoryOpen(false);
              }}
              aria-label="현재 채팅 질문 목록 열기"
              title="질문 목록"
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