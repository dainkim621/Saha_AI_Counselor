import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import type { Message } from "../App";
import gouni from "../assets/gouni-profile.png";
import remarkGfm from "remark-gfm";

const BACKEND_URL = "http://localhost:8000";

type ChatWindowProps = {
  messages: Message[];
  isLoading: boolean;
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

function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

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

              <div className="message-bubble assistant-bubble">
                답변 중...
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
                            <strong className="link-title">
                              {children}
                            </strong>
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