import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../App";
import gouni from "../assets/gouni-profile.png";
import remarkGfm from "remark-gfm";

// 백엔드 서버 주소
const BACKEND_URL = "http://localhost:8000";

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
  return content
    .split("\n")
    .map((line) => {
      const trimmedLine = line.trim();

      // 📍 1. 또는 📌 1. 형태의 문장을 제목으로 변환
      if (/^[📍📌]\s*\d+\./.test(trimmedLine)) {
        return `### ${trimmedLine}`;
      }

      // 담당 부서 안내와 관련 정보 링크 문장을 제목으로 변환
      if (
        trimmedLine === "📞 담당 부서 안내" ||
        trimmedLine === "🔗 관련 정보 링크"
      ) {
        return `### ${trimmedLine}`;
      }

      // 변환 조건에 해당하지 않으면 원래 문장을 그대로 반환
      return line;
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
  /*
   * 채팅창의 가장 아래쪽 요소를 가리키는 ref
   *
   * 새로운 메시지가 추가되면 이 위치로 자동 스크롤함
   */
  const bottomRef = useRef<HTMLDivElement | null>(null);

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

  /*
   * 메시지, 로딩 상태 또는 유사도 점수가 변경될 때마다
   * 채팅창을 가장 아래쪽으로 이동
   */
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading, similarityScore, feedbackStates]);

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
  const submitFeedback = async (payload: FeedbackPayload) => {
    console.log("만족도 평가 데이터:", payload);

    /*
     * 추후 백엔드 API 연결 시 아래 코드를 사용할 수 있음
     *
     * try {
     *   const response = await fetch(`${BACKEND_URL}/api/feedback`, {
     *     method: "POST",
     *     headers: {
     *       "Content-Type": "application/json",
     *     },
     *     body: JSON.stringify(payload),
     *   });
     *
     *   if (!response.ok) {
     *     throw new Error("만족도 평가 저장에 실패했습니다.");
     *   }
     * } catch (error) {
     *   console.error("만족도 평가 저장 오류:", error);
     * }
     */
  };

  /*
   * "도움이 됐어요" 버튼을 눌렀을 때 실행되는 함수
   *
   * 1. 해당 답변을 만족으로 표시
   * 2. 질문과 답변을 포함한 평가 데이터를 생성
   * 3. submitFeedback 함수로 전달
   */
  const handlePositiveFeedback = (
    messageIndex: number,
    answer: string
  ) => {
    // 해당 답변의 평가 상태를 만족 및 제출 완료로 변경
    setFeedbackStates((previousStates) => ({
      ...previousStates,
      [messageIndex]: {
        rating: "positive",
        showReasons: false,
        submitted: true,
      },
    }));

    // 해당 챗봇 답변 바로 앞의 사용자 질문 찾기
    const question = findPreviousUserQuestion(messageIndex);

    // 백엔드로 전달할 평가 데이터 생성
    const payload: FeedbackPayload = {
      messageIndex,
      question,
      answer,
      rating: "positive",
      reason: null,
    };

    // 만족도 평가 제출
    void submitFeedback(payload);
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

  /*
   * 사용자가 불만족 사유를 선택했을 때 실행되는 함수
   *
   * 1. 선택한 사유를 상태에 저장
   * 2. 평가 완료 상태로 변경
   * 3. 질문, 답변, 불만족 사유를 백엔드로 전달
   */
  const handleReasonSelect = (
    messageIndex: number,
    answer: string,
    reason: FeedbackReason
  ) => {
    // 선택한 불만족 사유와 평가 완료 상태 저장
    setFeedbackStates((previousStates) => ({
      ...previousStates,
      [messageIndex]: {
        rating: "negative",
        reason,
        showReasons: false,
        submitted: true,
      },
    }));

    // 해당 챗봇 답변 바로 앞의 사용자 질문 찾기
    const question = findPreviousUserQuestion(messageIndex);

    // 백엔드로 전달할 평가 데이터 생성
    const payload: FeedbackPayload = {
      messageIndex,
      question,
      answer,
      rating: "negative",
      reason,
    };

    // 만족도 평가 제출
    void submitFeedback(payload);
  };

  return (
    <div className="chat-window">
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
                    {similarityScore === null
                      ? "유사도 계산 중입니다."
                      : similarityScore >= 80
                      ? "✅ 신뢰할 수 있는 정보입니다."
                      : similarityScore >= 60
                      ? "🟡 참고할 수 있는 정보입니다."
                      : "⚠️ 참고 문서와의 유사도가 낮습니다."}
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
                        {message.similarityScore >= 80
                          ? "✅ 신뢰할 수 있는 정보입니다."
                          : message.similarityScore >= 60
                          ? "🟡 참고할 수 있는 정보입니다."
                          : "⚠️ 참고 문서와의 유사도가 낮습니다."}
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
                    {formatMarkdown(message.content)}
                  </ReactMarkdown>

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
                                📄
                              </div>

                              <div className="download-card-content">
                                <div className="download-card-title">
                                  {file.file_name}
                                </div>

                                <div className="download-card-subtitle">
                                  클릭하여 파일 다운로드
                                </div>
                              </div>

                              <div className="download-card-arrow">
                                →
                              </div>
                            </a>
                          )
                        )}
                      </div>
                    )}

                  {/*
                   * 챗봇 답변 만족도 평가 영역
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
                            >
                              👍 도움이 됐어요
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
                            >
                              👎 도움이 안 됐어요
                            </button>
                          </div>

                          {/*
                           * 사용자가 "도움이 안 됐어요"를 선택했을 때만
                           * 불만족 사유 선택 버튼 표시
                           */}
                          {currentFeedback.showReasons && (
                            <div className="feedback-reason-area">
                              <p className="feedback-reason-title">
                                어떤 점이 아쉬웠나요?
                              </p>

                              <div className="feedback-reason-list">
                                {feedbackReasons.map(
                                  (reason) => (
                                    <button
                                      key={reason.value}
                                      type="button"
                                      className="feedback-reason-button"
                                      onClick={() =>
                                        handleReasonSelect(
                                          index,
                                          message.content,
                                          reason.value
                                        )
                                      }
                                    >
                                      {reason.label}
                                    </button>
                                  )
                                )}
                              </div>
                            </div>
                          )}
                        </>
                      ) : (
                        /*
                         * 사용자가 평가를 완료한 뒤 표시되는 문구
                         */
                        <p className="feedback-complete-message">
                          {currentFeedback.rating ===
                          "positive"
                            ? "👍 소중한 의견 감사합니다."
                            : "의견이 전달되었습니다. 답변 개선에 참고하겠습니다."}
                        </p>
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

      {/* 새로운 메시지가 생길 때 자동 스크롤할 채팅창 마지막 위치 */}
      <div ref={bottomRef}></div>
    </div>
  );
}

export default ChatWindow;