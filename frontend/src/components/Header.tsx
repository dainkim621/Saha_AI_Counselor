function Header() {
  return (
    <header className="header">
      <div className="header-text">
        <p className="header-kicker">SAHA AI CIVIL SERVICE</p>

        <h1>사하구 AI 민원 상담사</h1>

        <p className="header-description">
          민원 서류, 신청 절차, 준비물을 쉽고 빠르게 안내해드려요.
        </p>

        <div className="header-badge-list">
          <span className="header-badge">AI 민원 안내</span>
          <span className="header-badge">서류·절차 안내</span>
          <span className="header-badge">24시간 상담 가능</span>
        </div>
      </div>
    </header>
  );
}

export default Header;