import { useEffect, useState } from "react";
import { Navigate } from "react-router-dom";

type ProtectedAdminRouteProps = {
  children: React.ReactNode;
};

function ProtectedAdminRoute({ children }: ProtectedAdminRouteProps) {
  // 서버에 관리자 로그인 상태를 확인하는 동안 사용
  const [isLoading, setIsLoading] = useState(true);

  // 관리자 인증 여부
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  useEffect(() => {
    const checkAdminLogin = async () => {
      try {
        const response = await fetch(
          "http://localhost:8000/admin/me",
          {
            // HttpOnly 세션 쿠키를 서버에 함께 전송
            credentials: "include",
          }
        );

        // /admin/me가 200이면 유효한 관리자 세션
        if (response.ok) {
          setIsAuthenticated(true);
        } else {
          setIsAuthenticated(false);
        }
      } catch (error) {
        console.error("관리자 인증 확인 중 오류:", error);
        setIsAuthenticated(false);
      } finally {
        // 인증 확인 완료
        setIsLoading(false);
      }
    };

    checkAdminLogin();
  }, []);

  // 서버의 인증 확인이 끝날 때까지 대시보드를 보여주지 않음
  if (isLoading) {
    return <div>관리자 인증 확인 중...</div>;
  }

  // 로그인되어 있지 않으면 로그인 페이지로 이동
  if (!isAuthenticated) {
    return <Navigate to="/admin/login" replace />;
  }

  // 인증된 관리자만 실제 관리자 페이지를 볼 수 있음
  return <>{children}</>;
}

export default ProtectedAdminRoute;