import { useEffect, useRef, useState } from "react";
import "./App.css";

import Header from "./components/Header";
import MascotCard from "./components/MascotCard";
import ChatWindow from "./components/ChatWindow";
import ChatInput from "./components/ChatInput";
import QuickMenu from "./components/QuickMenu";

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

// 브라우저 localStorage에 저장할 질문 기록 타입
type QuestionLog = {
  // 사용자가 입력한 질문
  question: string;

  // 질문이 입력된 날짜와 시간
  askedAt: string;
};

// 질문 기록이 없을 때 표시할 기본 FAQ
const defaultWeeklyQuestions = [
  "전입신고는 어떻게 하나요?",
  "여권 발급에 필요한 서류는 무엇인가요?",
  "무인민원발급기는 어디에 있나요?",
  "대형폐기물 배출은 어떻게 신청하나요?",
];

// localStorage에 질문 기록을 저장할 때 사용할 이름
const QUESTION_LOG_STORAGE_KEY = "weeklyQuestionLogs";

// 최근 질문으로 인정할 기간: 7일
const SEVEN_DAYS_IN_MS = 7 * 24 * 60 * 60 * 1000;

// QuickMenu에 표시할 최대 질문 개수
const WEEKLY_QUESTION_LIMIT = 4;

/**
 * 질문 앞뒤의 공백과 중복 공백을 정리하는 함수
 *
 * 예:
 * "  전입신고는   어떻게 하나요?  "
 * → "전입신고는 어떻게 하나요?"
 */
const normalizeQuestion = (question: string) => {
  return question.trim().replace(/\s+/g, " ");
};

/**
 * localStorage에서 저장된 질문 기록을 불러오는 함수
 *
 * 저장된 값이 없거나 JSON 형식이 잘못된 경우
 * 빈 배열을 반환한다.
 */
const getStoredQuestionLogs = (): QuestionLog[] => {
  try {
    const storedLogs = localStorage.getItem(QUESTION_LOG_STORAGE_KEY);

    // 아직 저장된 질문 기록이 없는 경우
    if (!storedLogs) {
      return [];
    }

    const parsedLogs = JSON.parse(storedLogs);

    // 저장된 데이터가 배열이 아니면 잘못된 데이터로 판단
    if (!Array.isArray(parsedLogs)) {
      return [];
    }

    return parsedLogs;
  } catch (error) {
    console.error("질문 기록 불러오기 오류:", error);
    return [];
  }
};

/**
 * 전체 질문 기록 중 최근 7일 이내에 입력된 질문만 반환
 */
const filterRecentQuestionLogs = (
  logs: QuestionLog[]
): QuestionLog[] => {
  // 현재 시간에서 7일을 뺀 시간
  const sevenDaysAgo = Date.now() - SEVEN_DAYS_IN_MS;

  return logs.filter((log) => {
    const askedTime = new Date(log.askedAt).getTime();

    return (
      // 날짜 형식이 정상이어야 함
      !Number.isNaN(askedTime) &&
      // 최근 7일 이내의 기록이어야 함
      askedTime >= sevenDaysAgo
    );
  });
};

/**
 * 최근 7일 질문을 입력 횟수 순으로 정렬하여
 * 상위 질문 목록을 반환하는 함수
 */
const calculateWeeklyQuestions = (
  logs: QuestionLog[]
): string[] => {
  /*
   * Map의 key:
   * 공백을 정리한 질문 문자열
   *
   * Map의 value:
   * 질문 원문, 입력 횟수, 마지막 입력 시간
   */
  const questionCount = new Map<
    string,
    {
      question: string;
      count: number;
      latestAskedAt: number;
    }
  >();

  logs.forEach((log) => {
    const normalizedQuestion = normalizeQuestion(log.question);

    // 공백뿐인 질문은 집계하지 않음
    if (!normalizedQuestion) {
      return;
    }

    const askedTime = new Date(log.askedAt).getTime();
    const existingQuestion =
      questionCount.get(normalizedQuestion);

    if (existingQuestion) {
      // 이미 등장한 질문이면 입력 횟수를 1 증가
      existingQuestion.count += 1;

      // 같은 질문이 마지막으로 입력된 시간 갱신
      existingQuestion.latestAskedAt = Math.max(
        existingQuestion.latestAskedAt,
        askedTime
      );
    } else {
      // 처음 등장한 질문이면 새로운 항목으로 등록
      questionCount.set(normalizedQuestion, {
        question: normalizedQuestion,
        count: 1,
        latestAskedAt: askedTime,
      });
    }
  });

  return Array.from(questionCount.values())
    .sort((a, b) => {
      // 1순위: 입력 횟수가 많은 질문
      if (b.count !== a.count) {
        return b.count - a.count;
      }

      // 2순위: 입력 횟수가 같으면 최근에 입력한 질문
      return b.latestAskedAt - a.latestAskedAt;
    })
    // 상위 4개까지만 사용
    .slice(0, WEEKLY_QUESTION_LIMIT)
    // QuickMenu에 필요한 질문 문자열만 반환
    .map((item) => item.question);
};

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
  const [weeklyQuestions, setWeeklyQuestions] = useState<string[]>(
    defaultWeeklyQuestions
  );

  // 마지막으로 읽은 assistant 메시지 인덱스 저장
  const lastSpokenIndexRef = useRef<number>(-1);

  // STT 녹음 객체 저장
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);

  // 마이크 스트림 저장
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // 녹음된 음성 조각 저장
  const audioChunksRef = useRef<Blob[]>([]);

  /**
   * 사용자가 실제로 전송한 질문을 localStorage에 저장하고,
   * 최근 7일 자주 묻는 질문 목록을 다시 계산하는 함수
   */
  const saveQuestionLog = (question: string) => {
    const normalizedQuestion = normalizeQuestion(question);

    // 공백뿐인 질문은 저장하지 않음
    if (!normalizedQuestion) {
      return;
    }

    // 기존에 저장된 질문 기록 불러오기
    const storedLogs = getStoredQuestionLogs();

    // 기존 기록 중 최근 7일 이내의 질문만 유지
    const recentLogs = filterRecentQuestionLogs(storedLogs);

    // 방금 입력한 질문을 새로운 기록으로 추가
    const updatedLogs: QuestionLog[] = [
      ...recentLogs,
      {
        question: normalizedQuestion,
        askedAt: new Date().toISOString(),
      },
    ];

    try {
      // 오래된 기록이 제거된 최신 질문 목록 저장
      localStorage.setItem(
        QUESTION_LOG_STORAGE_KEY,
        JSON.stringify(updatedLogs)
      );

      // 새 질문까지 포함하여 질문 순위 다시 계산
      const calculatedQuestions =
        calculateWeeklyQuestions(updatedLogs);

      // 집계된 질문이 있으면 집계 결과 표시
      if (calculatedQuestions.length > 0) {
        setWeeklyQuestions(calculatedQuestions);
      } else {
        // 질문 기록이 없으면 기본 FAQ 표시
        setWeeklyQuestions(defaultWeeklyQuestions);
      }
    } catch (error) {
      console.error("질문 기록 저장 오류:", error);
    }
  };

  /**
   * 페이지가 처음 열릴 때 localStorage에 저장된
   * 최근 7일 질문 기록을 불러온다.
   */
  useEffect(() => {
    // 저장된 전체 질문 기록 불러오기
    const storedLogs = getStoredQuestionLogs();

    // 최근 7일 이내의 기록만 남기기
    const recentLogs = filterRecentQuestionLogs(storedLogs);

    try {
      /*
       * 7일보다 오래된 기록을 제거한 배열을 다시 저장하여
       * localStorage에 불필요한 데이터가 계속 쌓이지 않도록 한다.
       */
      localStorage.setItem(
        QUESTION_LOG_STORAGE_KEY,
        JSON.stringify(recentLogs)
      );
    } catch (error) {
      console.error("질문 기록 정리 오류:", error);
    }

    // 최근 7일 질문의 입력 횟수 계산
    const calculatedQuestions =
      calculateWeeklyQuestions(recentLogs);

    if (calculatedQuestions.length > 0) {
      // 저장된 질문 기록이 있으면 실제 집계 결과 표시
      setWeeklyQuestions(calculatedQuestions);
    } else {
      // 저장된 질문 기록이 없으면 기본 FAQ 표시
      setWeeklyQuestions(defaultWeeklyQuestions);
    }
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

  // 사용자 질문을 백엔드로 전송하고 스트리밍 답변 수신
  const sendMessage = async (question: string) => {
    // 질문 앞뒤 공백 제거
    const trimmedQuestion = question.trim();

    // 빈 질문은 전송하지 않음
    if (!trimmedQuestion) return;

    // 이미 답변 생성 중이면 중복 전송하지 않음
    if (isLoading) return;

    /*
     * 사용자가 실제로 전송한 질문을 localStorage에 저장한다.
     *
     * 일반 입력창에서 보낸 질문과
     * QuickMenu를 눌러 전송한 질문 모두 이 함수를 거치므로
     * 모두 질문 기록에 포함된다.
     */
    saveQuestionLog(trimmedQuestion);

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

  return (
    <div className={`app ${fontModes[fontLevel]}`}>
      {/* 상단 헤더 */}
      <Header onGuideClick={() => setShowGuide(true)} />

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
          <button
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
          </button>
        </div>

        <div className="font-controls">
          <span>글자 크기</span>

          <button onClick={decreaseFont}>－</button>

          <div className="font-label">
            {fontLabels[fontLevel]}
          </div>

          <button onClick={increaseFont}>＋</button>
        </div>
      </div>

      {/* 메인 화면 영역 */}
      <main className="main-layout">
        <section className="left-section">
          <MascotCard />

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
          />
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