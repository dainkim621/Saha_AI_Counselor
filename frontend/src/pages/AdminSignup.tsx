import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import "../styles/AdminLogin.css";
import adminGouni from "../assets/admin-gouni.png";

function AdminSignup() {
  const navigate = useNavigate();

  // 회원가입 입력값
  const [username, setUsername] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [signupCode, setSignupCode] = useState("");

  // 오류 메시지
  const [errorMessage, setErrorMessage] = useState("");

  // 회원가입 요청 중인지 여부
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSignup = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();

    setErrorMessage("");

    // 프론트에서 기본 입력값 검사
    if (
      !username.trim() ||
      !name.trim() ||
      !password ||
      !passwordConfirm ||
      !signupCode.trim()
    ) {
      setErrorMessage("모든 항목을 입력해주세요.");
      return;
    }

    // 비밀번호 길이 검사
    if (password.length < 8) {
      setErrorMessage("비밀번호는 8자 이상 입력해주세요.");
      return;
    }

    // 비밀번호 확인
    if (password !== passwordConfirm) {
      setErrorMessage("비밀번호가 일치하지 않습니다.");
      return;
    }

    setIsSubmitting(true);

    try {
      const response = await fetch("http://localhost:8000/admin/signup", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          username: username.trim(),
          name: name.trim(),
          password,
          signup_code: signupCode.trim(),
        }),
      });

      if (!response.ok) {
        let message = "회원가입에 실패했습니다.";

        try {
          const data = await response.json();

          if (typeof data.detail === "string") {
            message = data.detail;
          }
        } catch {
          // 응답이 JSON 형식이 아닐 경우 기본 메시지 사용
        }

        setErrorMessage(message);
        return;
      }

      // 회원가입 성공 후 로그인 페이지로 이동
      navigate("/admin/login");
    } catch (error) {
      console.error("관리자 회원가입 요청 실패:", error);
      setErrorMessage(
        "서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요."
      );
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="admin-login-page">
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

        <div className="admin-login-card">
          <div className="admin-login-header">
            <h1>관리자 회원가입</h1>

            <p className="admin-login-description">
              관리자 계정을 생성하여 상담 현황을 관리하세요.
            </p>
          </div>

          <form 
            className="admin-login-form"
            onSubmit={handleSignup}
           >
            <div className="admin-login-field">
              <label htmlFor="username">관리자 ID</label>
              <input
                id="username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                placeholder="관리자 ID를 입력하세요"
                autoComplete="username"
              />
            </div>

            <div className="admin-login-field">
              <label htmlFor="name">관리자 이름</label>
              <input
                id="name"
                type="text"
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="관리자 이름을 입력하세요"
                autoComplete="name"
              />
            </div>

            <div className="admin-login-field">
              <label htmlFor="password">비밀번호</label>
              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                placeholder="8자 이상 입력하세요"
                autoComplete="new-password"
              />
            </div>

            <div className="admin-login-field">
              <label htmlFor="password-confirm">비밀번호 확인</label>
              <input
                id="password-confirm"
                type="password"
                value={passwordConfirm}
                onChange={(event) => setPasswordConfirm(event.target.value)}
                placeholder="비밀번호를 다시 입력하세요"
                autoComplete="new-password"
              />
            </div>

            <div className="admin-login-field">
              <label htmlFor="signup-code">관리자 가입 코드</label>
              <input
                id="signup-code"
                type="password"
                value={signupCode}
                onChange={(event) => setSignupCode(event.target.value)}
                placeholder="관리자 가입 코드를 입력하세요"
                autoComplete="off"
              />
            </div>
            
            {/* 회원가입 실패 메시지 */}
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
              disabled={isSubmitting}
            >
              {isSubmitting ? "가입 중..." : "회원가입"}
            </button>
          </form>

          <p className="admin-login-signup">
            이미 관리자 계정이 있으신가요?{" "}
            <Link to="/admin/login">로그인</Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default AdminSignup;