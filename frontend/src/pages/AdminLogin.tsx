import { useState } from "react";
import { useNavigate } from "react-router-dom";
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
    <main>
      <h1>관리자 로그인</h1>

      <form onSubmit={handleLogin}>
        {/* 관리자 아이디 */}
        <div>
          <label htmlFor="adminId">아이디</label>
          <input
            id="adminId"
            type="text"
            placeholder="관리자 아이디"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
        </div>

        {/* 관리자 비밀번호 */}
        <div>
          <label htmlFor="adminPassword">비밀번호</label>
          <input
            id="adminPassword"
            type="password"
            placeholder="비밀번호"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </div>

        {/* 로그인 실패 메시지 */}
        {errorMessage && (
          <p role="alert">
            {errorMessage}
          </p>
        )}

        <button 
          type="submit"
          disabled={isLoading}
        >
          {isLoading ? "로그인 중..." : "로그인"}
        </button>
      </form>
    </main>
  );
}

export default AdminLogin;