// 관리자 로그인 페이지
function AdminLogin() {
  return (
    <main>
      <h1>관리자 로그인</h1>

      <form>
        {/* 관리자 아이디 */}
        <div>
          <label htmlFor="adminId">아이디</label>
          <input
            id="adminId"
            type="text"
            placeholder="관리자 아이디"
          />
        </div>

        {/* 관리자 비밀번호 */}
        <div>
          <label htmlFor="adminPassword">비밀번호</label>
          <input
            id="adminPassword"
            type="password"
            placeholder="비밀번호"
          />
        </div>

        <button type="submit">
          로그인
        </button>
      </form>
    </main>
  );
}

export default AdminLogin;