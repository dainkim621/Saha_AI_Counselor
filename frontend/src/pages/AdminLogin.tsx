import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import "../styles/AdminLogin.css";
import adminGouni from "../assets/admin-gouni.png";

// 관리자 로그인 페이지
function AdminLogin() {
  // 관리자가 입력한 아이디와 비밀번호를 저장
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  // 로그인 실패 시 사용자에게 보여줄 오류 메시지
  const [errorMessage, setErrorMessage] = useState("");
  
  // 로그인 요청이 진행 중인지 확인
  const [isLoading, setIsLoading] = useState(false);

  // 로그인 성공 후 관리자 대시보드로 이동하기 위해 사용
  const navigate = useNavigate();

  // 로그인 폼 제출 처리
  const handleLogin = async (e: React.FormEvent<HTMLFormElement>) => {
    // form 제출 시 페이지가 새로고침되는 기본 동작 방지
    e.preventDefault();
    // 이미 로그인 요청 중이라면 중복 요청 방지
    if (isLoading) {
      return;
    }
    
    // 로그인 요청 시작
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8000/admin/login", {
        method: "POST",

        headers: {
          "Content-Type": "application/json",
        },

        // HttpOnly 세션 쿠키를 브라우저가 저장하고
        // 이후 요청에도 함께 보낼 수 있도록 설정
        credentials: "include",

        body: JSON.stringify({
          username: username,
          password: password,
        }),
      });

      const data = await response.json();
      
      // 로그인에 성공한 경우
      if (response.ok) {
        // 이전 오류 메시지가 있다면 제거
        setErrorMessage("");
        
        // 관리자 대시보드로 이동
        navigate("/admin");
        return;
      }
      
      // 로그인에 실패한 경우
      // FastAPI가 보내준 detail 메시지를 화면에 표시
      setErrorMessage(
        data.detail || "로그인에 실패했습니다."
      );

    } catch (error) {
      console.error("로그인 요청 중 오류:", error);

      // 백엔드 서버에 연결할 수 없는 경우
      setErrorMessage(
        "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
      );
    } finally {
      // 로그인 요청이 끝났으므로 다시 버튼을 누를 수 있도록 설정
      setIsLoading(false);
    }
  };
  return (
  <main className="admin-login-page">
    <div className="admin-login-container">

      {/* 관리자 시스템 브랜드 영역 */}
      <div className="admin-login-brand">
        <img
          src={adminGouni}
          alt=""
          className="admin-login-mascot"
        />

        <p className="admin-login-service-name">
          사하구 AI 민원 상담사
        </p>

        <span className="admin-login-badge">
          관리자 시스템
        </span>
      </div>

      {/* 실제 로그인 영역 */}
      <section className="admin-login-card">
        <div className="admin-login-header">
          <h1>관리자 로그인</h1>

          <p className="admin-login-description">
            관리자 계정으로 로그인하여 상담 현황을 관리하세요.
          </p>
        </div>

        <form
          className="admin-login-form"
          onSubmit={handleLogin}
        >
          {/* 관리자 아이디 */}
          <div className="admin-login-field">
            <label htmlFor="adminId">
              관리자 ID
            </label>

            <input
              id="adminId"
              type="text"
              placeholder="관리자 ID를 입력해주세요"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
            />
          </div>

          {/* 관리자 비밀번호 */}
          <div className="admin-login-field">
            <label htmlFor="adminPassword">
              비밀번호
            </label>

            <input
              id="adminPassword"
              type="password"
              placeholder="비밀번호를 입력해주세요"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
            />
          </div>

          {/* 로그인 실패 메시지 */}
          {errorMessage && (
            <div className="admin-login-error-area">
              <p
                className="admin-login-error"
                role="alert"
              >
                {errorMessage}
              </p>
            </div>
          )}
          <button
            className="admin-login-button"
            type="submit"
            disabled={isLoading}
          >
            {isLoading ? "로그인 중..." : "로그인"}
          </button>
        </form>

        <p className="admin-login-signup">
          관리자 계정이 없으신가요?{" "}
          <Link to="/admin/signup">
            회원가입
          </Link>
        </p>

        <p className="admin-login-notice">
          관리자 전용 페이지입니다.
        </p>
      </section>

    </div>
  </main>
);
}

export default AdminLogin;