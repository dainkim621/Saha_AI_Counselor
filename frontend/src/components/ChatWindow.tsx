import { useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../App";
import gouni from "../assets/gouni-profile.png";
import remarkGfm from "remark-gfm";

// 백엔드 서버 주소
const BACKEND_URL = "";

/*
 * ChatWindow 컴포넌트가 부모 컴포넌트로부터 전달받는 값
 *
 * messages:
 * 사용자와 챗봇이 주고받은 전체 메시지 목록
 *
 * isLoading:
 * 챗봇이 답변을 생성하고 있는지 나타내는 상태
 *
 * similarityScore:
 * 현재 생성 중인 답변의 참고 문서 매칭도
 */
type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
  similarityScore: number | null;
};

/*
 * 사용자가 선택할 수 있는 만족도 값
 *
 * positive: 도움이 됐어요
 * negative: 도움이 안 됐어요
 */
type FeedbackRating = "positive" | "negative";

/*
 * 불만족 사유 값
 *
 * inaccurate: 내용이 정확하지 않음
 * irrelevant: 질문과 관련이 없음
 * difficult: 설명이 이해하기 어려움
 * incomplete: 필요한 정보가 부족함
 */
type FeedbackReason =
  | "inaccurate"
  | "irrelevant"
  | "difficult"
  | "incomplete";

/*
 * 각 챗봇 답변의 평가 상태
 *
 * rating:
 * 사용자가 선택한 만족도
 *
 * reason:
 * 불만족인 경우 선택한 사유
 *
 * showReasons:
 * 불만족 사유 선택 영역을 보여줄지 여부
 *
 * submitted:
 * 평가 제출이 완료되었는지 여부
 */
type FeedbackState = {
  rating?: FeedbackRating;
  reason?: FeedbackReason;
  showReasons: boolean;
  submitted: boolean;
};

/*
 * 백엔드로 전달할 만족도 평가 데이터 형식
 *
 * 현재는 console.log()로만 확인하고,
 * 추후 백엔드 API가 만들어지면 이 데이터를 그대로 전송할 수 있음
 */
type FeedbackPayload = {
  messageIndex: number;
  question: string;
  answer: string;
  rating: FeedbackRating;
  reason: FeedbackReason | null;
};
/*
 * 챗봇 답변의 특정 문장을 마크다운 제목 형태로 변환하는 함수
 *
 * 예:
 * 📍 1. 신청 방법
 * → ### 📍 1. 신청 방법
 *
 * 이렇게 변환하면 ReactMarkdown이 해당 문장을 제목으로 표시함
 */
function formatMarkdown(content: string) {
  let isSuggestedQuestions = false;

  return content
    .split("\n")
    .map((line) => {
      const trimmedLine = line.trim();

      const plainLine = trimmedLine
        .replace(/^#{1,6}\s*/, "")
        .replace(/\*\*/g, "")
        .trim();

      // 하단 추천 질문 영역 시작
      if (
        /^(?:❓\s*)?(?:추천 파생 질문|이어서 궁금할 만한 질문)$/.test(plainLine)
      ) {
        isSuggestedQuestions = true;
        return "### ❓ 추천 파생 질문";
      }

      // 담당 부서 / 관련 링크
      if (
        plainLine === "📞 담당 부서 안내" ||
        plainLine === "🔗 관련 정보 링크"
      ) {
        return `### ${plainLine}`;
      }

      // 추천 질문 영역에서는 번호형 제목을 적용하지 않음
      if (isSuggestedQuestions) {
        return line;
      }

      // 주요 민원 안내에만 번호형 제목 적용
      const numberedHeading = trimmedLine.match(
        /^(?:#{1,6}\s*)?(?:📍|📌)?\s*\*{0,2}(\d+)\.\s*(.+)$/
      );

      if (numberedHeading) {
        const number = numberedHeading[1].padStart(2, "0");

        const title = numberedHeading[2]
          .replace(/^\*{1,2}|\*{1,2}$/g, "")
          .trim();

        return `### ${number}. ${title}`;
      }

      return line.replace(
        /^(\s*(?:(?:[-*+]|\d+\.)\s+)?)\s*(?:\p{Extended_Pictographic}|\p{Emoji_Presentation})(?:\uFE0F|\u200D\p{Extended_Pictographic})*\s*/u,
        "$1"
      );
    })
    .join("\n");
}
/*
 * 사용자에게 표시할 불만족 사유 목록
 *
 * value:
 * 백엔드와 DB에 저장할 값
 *
 * label:
 * 화면에 표시할 한글 문구
 */

// AI 답변을 본문과 추가 안내 영역으로 분리
function splitAnswerContent(content: string) {
  const lines = content.split("\n");

  // '담당 부서 안내'가 시작되는 줄 찾기
  const extraStartIndex = lines.findIndex((line) => {
    const title = line
      .trim()
      .replace(/^#{1,6}\s*/, "")
      .replace(/\*\*/g, "")
      .replace(/^📞\s*/, "")
      .trim();

    return title === "담당 부서 안내";
  });

  // 담당 부서 안내가 없으면 기존 답변 전체 유지
  if (extraStartIndex === -1) {
    return {
      mainContent: content,
      extraContent: "",
    };
  }

  return {
    mainContent: lines.slice(0, extraStartIndex).join("\n").trim(),
    extraContent: lines.slice(extraStartIndex).join("\n").trim(),
  };
}

function SimilarityStatusIcon({ score }: { score: number }) {
  const high = score >= 80;
  const medium = score >= 60 && score < 80;

  const color = high
    ? "#166534"
    : medium
    ? "#92400E"
    : "#991B1B";

  const background = high
    ? "#C5E8D0"
    : medium
    ? "#F8DFA6"
    : "#F5C9C6";

  return (
    <span
      className="similarity-status-icon"
      style={{ color, backgroundColor: background }}
      aria-hidden="true"
    >
      {high ? (
        <svg viewBox="0 0 24 24" fill="none">
          <path
            d="m5 12 4 4L19 6"
            stroke="currentColor"
            strokeWidth="2.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      ) : medium ? (
        <svg viewBox="0 0 24 24" fill="none">
          <circle
            cx="12"
            cy="12"
            r="9"
            stroke="currentColor"
            strokeWidth="2"
          />
          <path
            d="M12 11v5M12 8h.01"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      ) : (
        <svg viewBox="0 0 24 24" fill="none">
          <path
            d="M10.3 4.2 2.6 18a2 2 0 0 0 1.7 3h15.4a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0Z"
            stroke="currentColor"
            strokeWidth="1.8"
            strokeLinejoin="round"
          />
          <path
            d="M12 9v5M12 17h.01"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
          />
        </svg>
      )}
    </span>
  );
}

const feedbackReasons: {
  value: FeedbackReason;
  label: string;
}[] = [
  {
    value: "inaccurate",
    label: "내용이 정확하지 않아요",
  },
  {
    value: "irrelevant",
    label: "질문과 관련이 없어요",
  },
  {
    value: "difficult",
    label: "설명이 이해하기 어려워요",
  },
  {
    value: "incomplete",
    label: "필요한 정보가 부족해요",
  },
];

function ChatWindow({
  messages,
  isLoading,
  similarityScore,
}: ChatWindowProps) {

  const chatContainerRef = useRef<HTMLDivElement | null>(null);
  
  // 사용자가 최신 대화를 보고 있는지 여부
  const shouldAutoScrollRef = useRef(true);
  
  // 새 질문이 입력되었는지 확인하기 위한 값
  const previousUserCountRef = useRef(0);
  /*
   * 각 챗봇 답변의 만족도 평가 상태
   *
   * 메시지 배열의 index를 기준으로 평가 상태를 저장함
   *
   * 예:
   * {
   *   1: {
   *     rating: "positive",
   *     showReasons: false,
   *     submitted: true
   *   }
   * }
   */
  const [feedbackStates, setFeedbackStates] = useState<
    Record<number, FeedbackState>
  >({});
  
  // 사용자가 채팅창을 직접 스크롤했는지 확인
  const handleChatScroll = () => {
    const container = chatContainerRef.current;
    if (!container) return;

    const distanceToBottom =
      container.scrollHeight -
      container.scrollTop -
      container.clientHeight;

    // 최신 메시지 근처에 있을 때만 자동 스크롤
    shouldAutoScrollRef.current = distanceToBottom < 120;
  };

  // 새 질문 및 AI 답변이 추가될 때 자동 스크롤
  useEffect(() => {
    const container = chatContainerRef.current;
    if (!container) return;

    const userCount = messages.filter(
      (message) => message.role === "user"
    ).length;

    const isNewQuestion =
      userCount > previousUserCountRef.current;

    previousUserCountRef.current = userCount;

    // 처음 인사말만 있을 때는 이동하지 않음
    if (messages.length <= 1) return;

    // 새로운 질문을 하면 최신 대화로 이동
    if (isNewQuestion) {
      shouldAutoScrollRef.current = true;
    }

    // 사용자가 과거 답변을 읽고 있으면 이동 중단
    if (!shouldAutoScrollRef.current) return;

    const frame = requestAnimationFrame(() => {
      container.scrollTop = container.scrollHeight;
    });

    return () => cancelAnimationFrame(frame);
  }, [messages, isLoading, similarityScore]);




  /*
   * 특정 챗봇 답변 바로 앞에 있었던 사용자 질문을 찾는 함수
   *
   * 챗봇 답변의 index부터 위쪽으로 이동하면서
   * 가장 가까운 사용자 메시지를 반환함
   *
   * 만족도 평가를 저장할 때 질문과 답변을 함께 저장하기 위해 사용함
   */
  const findPreviousUserQuestion = (assistantMessageIndex: number) => {
    for (
      let index = assistantMessageIndex - 1;
      index >= 0;
      index -= 1
    ) {
      if (messages[index].role === "user") {
        return messages[index].content;
      }
    }

    // 이전 사용자 질문을 찾지 못한 경우 빈 문자열 반환
    return "";
  };

  /*
   * 만족도 평가를 백엔드로 전달하는 함수
   *
   * 현재는 백엔드 평가 API가 없으므로 console.log()로만 확인함
   *
   * 추후 POST /api/feedback 같은 API가 만들어지면
   * 이 함수 안에서 fetch를 사용하면 됨
   */
  const submitFeedback = async (payload: FeedbackPayload): Promise<boolean> => {
    console.log("만족도 평가 데이터:", payload);

    try {
      const response = await fetch(`${BACKEND_URL}/api/feedback`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        throw new Error("만족도 평가 저장에 실패했습니다.");
      }

      return true;
    } catch (error) {
      console.error("만족도 평가 저장 오류:", error);
      return false;
    }
  };

  /*
   * "도움이 됐어요" 버튼을 눌렀을 때 실행되는 함수
   *
   * 1. 해당 답변을 만족으로 표시
   * 2. 질문과 답변을 포함한 평가 데이터를 생성
   * 3. submitFeedback 함수로 전달
   */
  const handlePositiveFeedback = async (
    messageIndex: number,
    answer: string
  ) => {
    const question = findPreviousUserQuestion(messageIndex);

    const payload: FeedbackPayload = {
      messageIndex,
      question,
      answer,
      rating: "positive",
      reason: null,
    };

    const success = await submitFeedback(payload);

    if (!success) {
      alert("만족도 평가 저장에 실패했습니다. 다시 시도해 주세요.");
      return;
    }

    setFeedbackStates((previousStates) => ({
      ...previousStates,
      [messageIndex]: {
        rating: "positive",
        showReasons: false,
        submitted: true,
      },
    }));
  };

  /*
   * "도움이 안 됐어요" 버튼을 눌렀을 때 실행되는 함수
   *
   * 바로 평가를 제출하지 않고,
   * 먼저 불만족 사유 선택 버튼을 화면에 표시함
   */

  const handleNegativeFeedbackClick = (messageIndex: number) => {
    setFeedbackStates((previousStates) => ({
      ...previousStates,
      [messageIndex]: {
        rating: "negative",
        showReasons: true,
        submitted: false,
      },
    }));
  };

  const handleNegativeFeedbackSubmit = async (
    messageIndex: number,
    answer: string
  ) => {
    const selectedReason = feedbackStates[messageIndex]?.reason;

    if (!selectedReason) return;

    const question = findPreviousUserQuestion(messageIndex);

    const payload: FeedbackPayload = {
      messageIndex,
      question,
      answer,
      rating: "negative",
      reason: selectedReason,
    };

    const success = await submitFeedback(payload);

    if (!success) {
      alert("의견 저장에 실패했습니다. 다시 시도해 주세요.");
      return;
    }

    setFeedbackStates((previousStates) => ({
      ...previousStates,
      [messageIndex]: {
        rating: "negative",
        reason: selectedReason,
        showReasons: false,
        submitted: true,
      },
    }));
  };

  /*
   * 사용자가 불만족 사유를 선택했을 때 실행되는 함수
   *
   * 1. 선택한 사유를 상태에 저장
   * 2. 평가 완료 상태로 변경
   * 3. 질문, 답변, 불만족 사유를 백엔드로 전달
   */
  
    const handleReasonSelect = (
      messageIndex: number,
      reason: FeedbackReason
    ) => {
      // 사유 선택만 저장하고 아직 제출하지 않음
      setFeedbackStates((previousStates) => ({
        ...previousStates,
        [messageIndex]: {
          rating: "negative",
          reason,
          showReasons: true,
          submitted: false,
        },
      }));
    };
  

  return (
    <div className="chat-window"
      ref={chatContainerRef}
      onScroll={handleChatScroll}
    >
      {/* 전체 채팅 메시지를 순서대로 화면에 출력 */}
      {messages.map((message, index) => {
        /*
         * 현재 메시지에 저장된 만족도 평가 상태
         *
         * 아직 평가하지 않은 메시지는 기본 상태를 사용함
         */
        const currentFeedback: FeedbackState =
          feedbackStates[index] ?? {
            showReasons: false,
            submitted: false,
          };

        /*
         * 현재 챗봇 답변보다 앞에 사용자 질문이 있는지 확인
         *
         * 처음 표시되는 인사 메시지는 앞에 사용자 질문이 없기 때문에
         * 만족도 평가가 표시되지 않음
         */
        const previousUserQuestion =
          findPreviousUserQuestion(index);

        /*
         * 현재 메시지가 전체 메시지 중 마지막 메시지인지 확인
         *
         * 답변 스트리밍 중인 메시지는 일반적으로
         * 메시지 목록의 마지막에 위치함
         */
        const isLastMessage =
          index === messages.length - 1;

        /*
         * 현재 마지막 챗봇 답변이 생성 중인지 확인
         *
         * isLoading이 true인 동안에는 답변 글자가
         * 스트리밍 방식으로 출력되고 있는 상태임
         */
        const isCurrentAnswerStreaming =
          message.role === "assistant" &&
          isLastMessage &&
          isLoading;

        /*
         * 만족도 평가 영역을 표시할 조건
         *
         * 1. 챗봇이 작성한 메시지여야 함
         * 2. 해당 답변 앞에 사용자 질문이 있어야 함
         * 3. 답변 내용이 비어 있지 않아야 함
         * 4. 현재 답변이 스트리밍 중인 상태가 아니어야 함
         *
         * 따라서 처음 인사 메시지와 답변 생성 중에는
         * 만족도 평가가 표시되지 않음
         */
        const shouldShowFeedback =
          message.role === "assistant" &&
          previousUserQuestion.trim() !== "" &&
          message.content.trim() !== "" &&
          !isCurrentAnswerStreaming;

        
        // AI 답변을 본문과 추가 안내 영역으로 분리
        const { mainContent, extraContent } =
          message.role === "assistant"
          ? splitAnswerContent(message.content)
          : { mainContent: message.content, extraContent: "" };

        /*
         * 챗봇 메시지는 생성되었지만 아직 답변 내용이 없는 경우
         *
         * "답변 준비중..." 문구와 현재 계산 중인 유사도 정보를 표시함
         */
        if (
          message.role === "assistant" &&
          !message.content.trim() &&
          (!message.files || message.files.length === 0)
        ) {
          return (
            <div
              key={index}
              className="message-row assistant-row"
            >
              {/* 답변 생성 중인 챗봇 프로필 이미지 */}
              <img
                src={gouni}
                alt="고우니"
                className="chat-avatar chat-avatar-active"
              />

              <div className="message-bubble assistant-bubble loading-bubble">
                {/* 답변 생성 중임을 사용자에게 안내 */}
                <div className="loading-text">
                  답변 준비중...
                </div>

                <p className="loading-description">
                  문의하신 내용과 관련된 정보를 확인하고 있습니다.
                </p>

                {/* 현재 계산 중인 참고 정보 매칭도 */}
                <div className="similarity-card similarity-card-fixed">
                  <div className="similarity-card-header">
                    <span className="similarity-label">
                      참고 정보 매칭도
                    </span>

                    <span className="similarity-score">
                      {similarityScore !== null
                        ? `${similarityScore}%`
                        : "계산 중"}
                    </span>
                  </div>

                  {/* 유사도 점수를 막대그래프로 표시 */}
                  <div className="similarity-bar">
                    <div
                      className="similarity-bar-fill"
                      style={{
                        width:
                          similarityScore !== null
                            ? `${Math.min(
                                Math.max(
                                  similarityScore,
                                  0
                                ),
                                100
                              )}%`
                            : "0%",
                      }}
                    />
                  </div>

                  {/* 유사도 점수 구간에 따른 안내 문구 */}
                  <p className="similarity-desc">
                    {similarityScore !== null && (
                      <SimilarityStatusIcon score={similarityScore} />
                    )}

                    {similarityScore === null
                      ? "유사도 계산 중입니다."
                      : similarityScore >= 80
                      ? "신뢰할 수 있는 정보입니다."
                      : similarityScore >= 60
                      ? "참고할 수 있는 정보입니다."
                      : "참고 문서와의 유사도가 낮습니다."}
                  </p>
                </div>
              </div>
            </div>
          );
        }

        /*
         * 사용자 메시지 또는 내용이 있는 챗봇 메시지를 출력
         */
        return (
          <div
            key={index}
            className={
              message.role === "user"
                ? "message-row user-row"
                : "message-row assistant-row"
            }
          >
            {/* 챗봇 메시지인 경우에만 고우니 프로필 이미지 표시 */}
            {message.role === "assistant" && (
              <img
                src={gouni}
                alt="고우니"
                className="chat-avatar"
              />
            )}

            <div
              className={
                message.role === "user"
                  ? "message-bubble user-bubble"
                  : "message-bubble assistant-bubble"
              }
            >
              {message.role === "assistant" ? (
                /*
                 * 챗봇 답변 영역
                 *
                 * 마크다운 답변, 파일 다운로드,
                 * 만족도 평가 기능을 포함함
                 */
                <div className="markdown-content">
                  {/*
                   * 해당 메시지에 저장된 유사도 점수가 있는 경우 표시
                   *
                   * 유사도 카드는 답변 스트리밍 중에도
                   * 기존과 동일하게 답변 위쪽에 먼저 표시됨
                   */}
                  {message.similarityScore !== undefined && (
                    <div className="similarity-card similarity-card-fixed">
                      <div className="similarity-card-header">
                        <span className="similarity-label">
                          참고 정보 매칭도
                        </span>

                        <span className="similarity-score">
                          {message.similarityScore}%
                        </span>
                      </div>

                      {/* 저장된 유사도 점수를 막대그래프로 표시 */}
                      <div className="similarity-bar">
                        <div
                          className="similarity-bar-fill"
                          style={{
                            width: `${Math.min(
                              Math.max(
                                message.similarityScore,
                                0
                              ),
                              100
                            )}%`,
                          }}
                        />
                      </div>

                      {/* 유사도 점수에 따른 신뢰도 안내 문구 */}
                      <p className="similarity-desc">
                        <SimilarityStatusIcon score={message.similarityScore} />

                        {message.similarityScore >= 80
                          ? "신뢰할 수 있는 정보입니다."
                          : message.similarityScore >= 60
                          ? "참고할 수 있는 정보입니다."
                          : "참고 문서와의 유사도가 낮습니다."}
                      </p>
                    </div>
                  )}

                  {/*
                   * 챗봇 답변을 마크다운 형식으로 출력
                   *
                   * remarkGfm:
                   * 표, 취소선, 체크박스 등 GitHub 스타일 마크다운 지원
                   */}
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      /*
                       * 굵은 글씨를 출력할 때 특정 제목이면
                       * 별도의 CSS 클래스를 적용
                       */
                      h3: ({ children }) => {
                        const headingText = String(children).trim();

                        const match = headingText.match(/^(\d{2})\.\s*(.+)$/);

                        if (match) {
                          return (
                            <h3 className="answer-numbered-heading">
                              <span className="answer-heading-number">
                                {match[1]}
                              </span>

                              <span className="answer-heading-title">
                                {match[2]}
                              </span>
                            </h3>
                          );
                        }

                        return <h3>{children}</h3>;
                      },
                      strong: ({ children }) => {
                        const text =
                          children?.toString() ?? "";

                        if (
                          text.includes("담당 부서 안내")
                        ) {
                          return (
                            <strong className="department-title">
                              {children}
                            </strong>
                          );
                        }

                        if (
                          text.includes("관련 정보 링크")
                        ) {
                          return (
                            <strong className="link-title">
                              {children}
                            </strong>
                          );
                        }

                        return (
                          <strong>{children}</strong>
                        );
                      },

                      /*
                       * 답변에 포함된 링크를 새 탭에서 열도록 설정
                       */
                      a: ({ href, children }) => (
                        <a
                          href={href}
                          target="_blank"
                          rel="noreferrer"
                          style={{
                            color: "#2563eb",
                            textDecoration: "underline",
                          }}
                        >
                          {children}
                        </a>
                      ),
                    }}
                  >
                    {formatMarkdown(mainContent)}
                  </ReactMarkdown>

                  {/* 추가 안내 및 자료 영역 */}
                  {(extraContent || (message.files && message.files.length > 0)) && (
                    <div className="answer-extra-panel">
                      <h4>추가 안내 및 자료</h4>

                      {extraContent && (
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            h3: ({ children }) => {
                              const heading = String(children).trim();

                              const config = [
                                {
                                  match: "담당 부서 안내",
                                  label: "담당 부서",
                                  icon: (
                                    <svg viewBox="0 0 24 24" fill="none"
                                      stroke="currentColor" strokeWidth="1.8"
                                      strokeLinecap="round" strokeLinejoin="round">
                                      <rect x="4" y="3" width="12" height="18" rx="1.5" />
                                      <path d="M16 10h4v11M2 21h20M8 7h4M8 11h4M8 15h4" />
                                    </svg>
                                  ),
                                },
                                {
                                  match: "관련 정보 링크",
                                  label: "관련 정보",
                                  icon: (
                                    <svg viewBox="0 0 24 24" fill="none"
                                      stroke="currentColor" strokeWidth="1.8"
                                      strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M13 5H6a3 3 0 0 0-3 3v10a3 3 0 0 0 3 3h10a3 3 0 0 0 3-3v-7" />
                                      <path d="M14 3h7v7M21 3l-10 10" />
                                    </svg>
                                  ),
                                },
                                {
                                  match: "추천 파생 질문",
                                  label: "이어서 물어볼 질문",
                                  icon: (
                                    <svg viewBox="0 0 24 24" fill="none"
                                      stroke="currentColor" strokeWidth="1.8"
                                      strokeLinecap="round" strokeLinejoin="round">
                                      <path d="M20 11.5a7 7 0 0 1-7 7H7l-4 3v-6a7 7 0 0 1 7-7h3a7 7 0 0 1 7 3Z" />
                                      <path d="M8 6a6 6 0 0 1 6-4h3a6 6 0 0 1 6 6v6l-3-2" />
                                    </svg>
                                  ),
                                },
                              ];

                              const section = config.find((item) =>
                                heading.includes(item.match)
                              );

                              if (!section) return <h3>{children}</h3>;

                              return (
                                <div className="answer-extra-section-heading">
                                  <span className="answer-extra-section-icon">
                                    {section.icon}
                                  </span>
                                  <span className="answer-extra-label">
                                    {section.label}
                                  </span>
                                </div>
                              );
                            },

                            a: ({ href, children }) => (
                              <a href={href} target="_blank" rel="noreferrer">
                                {children}
                              </a>
                            ),
                          }}
                        >
                          {formatMarkdown(extraContent)}
                        </ReactMarkdown>
                      )}

                  {/*
                   * 챗봇 답변에 다운로드 파일이 포함된 경우
                   * 파일마다 다운로드 카드 표시
                   */}
                  {message.files &&
                    message.files.length > 0 && (
                      <div className="download-buttons-container">
                        {message.files.map(
                          (file, fileIndex) => (
                            <a
                              key={fileIndex}
                              href={
                                /*
                                 * 사하구청 원본 다운로드 주소인 경우
                                 * 주소를 그대로 사용
                                 *
                                 * 백엔드가 제공하는 파일인 경우
                                 * 백엔드 주소를 앞에 붙여 사용
                                 */
                                file.file_url.includes(
                                  "FileDown.do"
                                )
                                  ? file.file_url
                                  : `${BACKEND_URL}${file.file_url}`
                              }
                              download
                              className="download-card"
                            >
                              <div className="download-card-icon">
                                <svg
                                  width="24"
                                  height="24"
                                  viewBox="0 0 24 24"
                                  fill="none"
                                  stroke="currentColor"
                                  strokeWidth="1.8"
                                  strokeLinecap="round"
                                  strokeLinejoin="round"
                                  aria-hidden="true"
                                >
                                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z" />
                                  <path d="M14 2v6h6" />
                                  <path d="M8 13h8" />
                                  <path d="M8 17h8" />
                                </svg>
                              </div>

                              <div className="download-card-content">
                                <div className="download-card-title">
                                  {file.file_name}
                                </div>
                              </div>

                              <div className="download-card-arrow">
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
                                  <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                                  <path d="m7 10 5 5 5-5" />
                                  <path d="M12 15V3" />
                                </svg>
                              </div>
                            </a>
                                                    )
                        )}
                      </div>
                    )}

                  </div>
                )}

                  {/*
                    챗봇 답변 만족도 평가 영역
                   *
                   * 처음 인사 메시지에는 표시되지 않음
                   *
                   * 답변이 스트리밍되는 동안에는 표시되지 않고,
                   * 답변 생성이 모두 끝난 뒤에 표시됨
                   *
                   * 평가 제출 전에는 만족/불만족 버튼을 표시하고,
                   * 평가 제출 후에는 완료 문구를 표시함
                   */}
                  {shouldShowFeedback && (
                    <div className="answer-feedback">
                      {!currentFeedback.submitted ? (
                       <>
                        {!currentFeedback.showReasons && (
                          <>
                            <p className="feedback-question">
                              이 답변이 도움이 되었나요?
                            </p>

                            <div className="feedback-button-group">
                            {/* 만족 평가 버튼 */}
                            <button
                              type="button"
                              className="feedback-button positive-feedback-button"
                              onClick={() =>
                                handlePositiveFeedback(
                                  index,
                                  message.content
                                )
                              }
                              aria-label="도움이 됐어요"
                              title="도움이 됐어요"
                            >
                              <svg
                                width="18"
                                height="18"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                aria-hidden="true"
                              >
                                <path d="M7 10v12" />
                                <path d="M15 5.88 14 10h5.83a2 2 0 0 1 1.92 2.56l-2.33 8A2 2 0 0 1 17.5 22H5a2 2 0 0 1-2-2v-8a2 2 0 0 1 2-2h2.76a2 2 0 0 0 1.79-1.11L12.6 3a3.13 3.13 0 0 1 3 2.88Z" />
                              </svg>
                            </button>

                            {/* 불만족 사유 선택 영역을 여는 버튼 */}
                            <button
                              type="button"
                              className="feedback-button negative-feedback-button"
                              onClick={() =>
                                handleNegativeFeedbackClick(
                                  index
                                )
                              }

                              aria-label="도움이 안 됐어요"
                              title="도움이 안 됐어요"
                            >
                              <svg
                                width="18"
                                height="18"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke="currentColor"
                                strokeWidth="2"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                aria-hidden="true"
                              >
                                <path d="M17 14V2" />
                                <path d="M9 18.12 10 14H4.17a2 2 0 0 1-1.92-2.56l2.33-8A2 2 0 0 1 6.5 2H19a2 2 0 0 1 2 2v8a2 2 0 0 1-2 2h-2.76a2 2 0 0 0-1.79 1.11L11.4 21a3.13 3.13 0 0 1-3-2.88Z" />
                              </svg>
                            </button>
                          </div>
                        </>
                      )}

                          {/*
                           * 사용자가 "도움이 안 됐어요"를 선택했을 때만
                           * 불만족 사유 선택 버튼 표시
                           */}
                          {currentFeedback.showReasons && (
                            <div className="feedback-reason-area">
                              <p className="feedback-reason-title">
                                어떤 점이 아쉬우셨나요?
                              </p>

                              <div className="feedback-reason-list">
                                {feedbackReasons.map(
                                  (reason) => (
                                    
                                    <button
                                      key={reason.value}
                                      type="button"
                                      className={`feedback-reason-button ${
                                        currentFeedback.reason === reason.value ? "selected" : ""
                                      }`}
                                      aria-pressed={currentFeedback.reason === reason.value}
                                      onClick={() =>
                                        handleReasonSelect(index, reason.value)
                                      }
                                    >
                                      <span
                                        className="feedback-reason-radio"
                                        aria-hidden="true"
                                      />
                                      <span>{reason.label}</span>
                                    </button>

                                  
                                  )
                                )}
                              </div>

                              <button
                                type="button"
                                className="feedback-submit-button"
                                disabled={!currentFeedback.reason}
                                onClick={() =>
                                  handleNegativeFeedbackSubmit(
                                    index,
                                    message.content
                                  )
                                }
                              >
                                의견 제출
                              </button>
                            </div>
                          )}

                        </>
                      ) : (
                        /*
                         * 사용자가 평가를 완료한 뒤 표시되는 문구
                         */
                        
                        <div className="feedback-complete-message">
                          <svg
                            width="16"
                            height="16"
                            viewBox="0 0 24 24"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            aria-hidden="true"
                          >
                            <circle cx="12" cy="12" r="10" />
                            <path d="m8 12 2.5 2.5L16 9" />
                          </svg>

                          <span>
                            {currentFeedback.rating === "positive"
                              ? "소중한 평가 감사합니다."
                              : "의견을 보내주셔서 감사합니다. 더 나은 답변을 제공하는 데 참고하겠습니다."}
                          </span>
                        </div>

                      )}
                    </div>
                  )}
                </div>
              ) : (
                /*
                 * 사용자 메시지는 별도의 마크다운 처리 없이
                 * 입력한 내용을 그대로 표시
                 */
                message.content
              )}
            </div>
          </div>
        );
      })}
      
    </div>
  );
}

export default ChatWindow;