import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../App";
import gouni from "../assets/gouni-profile.png";
import remarkGfm from "remark-gfm";

const BACKEND_URL = "http://localhost:8000";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
  similarityScore: number | null;
};

function formatMarkdown(content: string) {
  return content
    .split("\n")
    .map((line) => {
      const trimmedLine = line.trim();

      if (/^[📍📌]\s*\d+\./.test(trimmedLine)) {
        return `### ${trimmedLine}`;
      }

      if (
        trimmedLine === "📞 담당 부서 안내" ||
        trimmedLine === "🔗 관련 정보 링크"
      ) {
        return `### ${trimmedLine}`;
      }

      return line;
    })
    .join("\n");
}

function ChatWindow({ messages, isLoading, similarityScore }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading, similarityScore]);

  return (
    <div className="chat-window">
      {messages.map((message, index) => {
        if (
          message.role === "assistant" &&
          !message.content.trim() &&
          (!message.files || message.files.length === 0)
        ) {
          return (
            <div key={index} className="message-row assistant-row">
              <img
                src={gouni}
                alt="고우니"
                className="chat-avatar chat-avatar-active"
              />

              <div className="message-bubble assistant-bubble loading-bubble">
                <div className="loading-text">답변 준비중...</div>

                <div className="similarity-card similarity-card-fixed">
                  <div className="similarity-card-header">
                    <span className="similarity-label">참고 정보 매칭도</span>
                    <span className="similarity-score">
                      {similarityScore !== null
                        ? `${similarityScore}%`
                        : "계산 중"}
                    </span>
                  </div>

                  <div className="similarity-bar">
                    <div
                      className="similarity-bar-fill"
                      style={{
                        width:
                          similarityScore !== null
                            ? `${Math.min(
                                Math.max(similarityScore, 0),
                                100
                              )}%`
                            : "0%",
                      }}
                    />
                  </div>

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

        return (
          <div
            key={index}
            className={
              message.role === "user"
                ? "message-row user-row"
                : "message-row assistant-row"
            }
          >
            {message.role === "assistant" && (
              <img src={gouni} alt="고우니" className="chat-avatar" />
            )}

            <div
              className={
                message.role === "user"
                  ? "message-bubble user-bubble"
                  : "message-bubble assistant-bubble"
              }
            >
              {message.role === "assistant" ? (
                <div className="markdown-content">
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

                      <div className="similarity-bar">
                        <div
                          className="similarity-bar-fill"
                          style={{
                            width: `${Math.min(
                              Math.max(message.similarityScore, 0),
                              100
                            )}%`,
                          }}
                        />
                      </div>

                      <p className="similarity-desc">
                        {message.similarityScore >= 80
                          ? "✅ 신뢰할 수 있는 정보입니다."
                          : message.similarityScore >= 60
                          ? "🟡 참고할 수 있는 정보입니다."
                          : "⚠️ 참고 문서와의 유사도가 낮습니다."}
                      </p>
                    </div>
                  )}

                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{
                      strong: ({ children }) => {
                        const text = children?.toString() ?? "";

                        if (text.includes("담당 부서 안내")) {
                          return (
                            <strong className="department-title">
                              {children}
                            </strong>
                          );
                        }

                        if (text.includes("관련 정보 링크")) {
                          return (
                            <strong className="link-title">{children}</strong>
                          );
                        }

                        return <strong>{children}</strong>;
                      },

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

                  {message.files && message.files.length > 0 && (
                    <div className="download-buttons-container">
                      {message.files.map((file, fileIndex) => (
                        <a
                          key={fileIndex}
                          href={
                            file.file_url.includes("FileDown.do")
                              ? file.file_url
                              : `${BACKEND_URL}${file.file_url}`
                          }
                          download
                          className="download-card"
                        >
                          <div className="download-card-icon">📄</div>

                          <div className="download-card-content">
                            <div className="download-card-title">
                              {file.file_name}
                            </div>

                            <div className="download-card-subtitle">
                              클릭하여 파일 다운로드
                            </div>
                          </div>

                          <div className="download-card-arrow">→</div>
                        </a>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                message.content
              )}
            </div>
          </div>
        );
      })}

      <div ref={bottomRef}></div>
    </div>
  );
}

export default ChatWindow;