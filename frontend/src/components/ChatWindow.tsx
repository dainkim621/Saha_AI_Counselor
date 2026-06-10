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

function ChatWindow({ messages, isLoading }: ChatWindowProps) {
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth",
    });
  }, [messages, isLoading]);

  return (
    <div className="chat-window">
      {messages.map((message, index) => (
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
              // 💡 말풍선 내부에는 순수하게 GPT의 친절한 답변 텍스트만 렌더링합니다.
              <div>
                <ReactMarkdown
                  remarkPlugins={[remarkGfm]}
                  components={{
                    a: ({ href, children }) => (
                      <a href={href} target="_blank" rel="noreferrer" style={{ color: "#2563eb", textDecoration: "underline" }}>
                        {children}
                      </a>
                    ),
                  }}
                >
                  {message.content}
                </ReactMarkdown>

                {/* 💡 [핵심 추가] 백엔드가 files 배열을 보내줬고, 내용이 존재한다면 말풍선 하단에 버튼을 동적으로 생성합니다! */}
                {message.files && message.files.length > 0 && (
                  <div className="download-buttons-container" style={{ marginTop: "4px" }}>
                    {message.files.map((file, fileIndex) => (
                      <a
                        key={fileIndex}
                        href={file.file_url.includes("FileDown.do") ? file.file_url : `${BACKEND_URL}${file.file_url}`}
                        download
                        className="download-btn"
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "6px",
                          backgroundColor: "#10b981", // 수빈님이 지정해 둔 이쁜 초록색
                          color: "#ffffff",
                          fontWeight: "bold",
                          padding: "6px 12px",
                          borderRadius: "6px",
                          marginTop: "8px",
                          marginRight: "8px", // 여러 개일 때를 대비한 간격
                          fontSize: "14px",
                          textDecoration: "none"
                        }}
                      >
                        📥 {file.file_name} 다운로드 받기
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
      ))}

      {isLoading && (
        <div className="message-row assistant-row">
          <img
            src={gouni}
            alt="고우니 프로필"
            className="chat-avatar chat-avatar-active"
          />

          <div className="message-bubble assistant-bubble">
            고우니가 답변을 준비하고 있어요...
          </div>
        </div>
      )}

      <div ref={bottomRef}></div>
    </div>
  );
}

export default ChatWindow;