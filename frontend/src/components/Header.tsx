import gouni from "../assets/gouni.png";

function Header() {
  return (
    <header className="header">
      <div className="header-pattern pattern-1">💬</div>
      <div className="header-pattern pattern-2">📄</div>
      <div className="header-pattern pattern-3">✨</div>
      <div className="header-pattern pattern-4">🏢</div>

      <div className="header-content">
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

          <div className="header-info-cards">
            <div className="info-card">
              <span>📄</span>
              <p>민원 안내</p>
            </div>

            <div className="info-card">
              <span>🤖</span>
              <p>AI 상담</p>
            </div>

            <div className="info-card">
              <span>🕒</span>
              <p>24시간</p>
            </div>
          </div>
        </div>

        <div className="header-visual">
          <img src={gouni} alt="고우니" className="header-gouni" />
        </div>
      </div>
    </header>
  );
}

export default Header;