import gouni from "../assets/gouni.png";

function Header() {
  return (
    <header className="header">
      {/* 은은한 배경 원형 레이어 */}
      <div className="header-bg-circle circle-left"></div>
      <div className="header-bg-circle circle-right"></div>

      {/* 중앙과 주변 빈 공간을 채워줄 은은한 테크/민원 그래픽 패턴들 */}
      <div className="header-pattern pattern-1">
        <svg width="46" height="46" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
        </svg>
      </div>
      <div className="header-pattern pattern-2">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
          <polyline points="14 2 14 8 20 8"></polyline>
          <line x1="16" y1="13" x2="8" y2="13"></line>
          <line x1="16" y1="17" x2="8" y2="17"></line>
          <polyline points="10 9 9 9 8 9"></polyline>
        </svg>
      </div>
      <div className="header-pattern pattern-3">✨</div>
      <div className="header-pattern pattern-4">
        <svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10"></circle>
          <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
          <line x1="12" y1="17" x2="12.01" y2="17"></line>
        </svg>
      </div>
      {/* 추가 패턴 5: 돋보기 */}
      <div className="header-pattern pattern-5">
        <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
      </div>
      {/* 추가 패턴 6: 체크박스 */}
      <div className="header-pattern pattern-6">
        <svg width="38" height="38" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <polyline points="9 11 12 14 22 4"></polyline>
          <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"></path>
        </svg>
      </div>
      {/* 추가 패턴 7: 전구 */}
      <div className="header-pattern pattern-7">
        <svg width="42" height="42" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M15 14c.2-1 .7-1.7 1.5-2.5 1-.9 1.5-2.2 1.5-3.5A5 5 0 0 0 8 8c0 1.3.5 2.5 1.5 3.5.8.8 1.3 1.5 1.5 2.5"></path>
          <line x1="9" y1="18" x2="15" y2="18"></line>
          <line x1="10" y1="22" x2="14" y2="22"></line>
        </svg>
      </div>

      <div className="header-content">
        {/* 왼쪽: 타이틀 및 정보 영역 */}
        <div className="header-text">
          <p className="header-kicker">SAHA AI CIVIL SERVICE</p>
          <h1>사하구 AI 민원 상담사</h1>
          <p className="header-description">
            민원 서류, 신청 절차, 준비물을 쉽고 빠르게 안내해드려요.
          </p>
          <div className="header-badge-list">
            <span className="header-badge">🤖 AI 민원 안내</span>
            <span className="header-badge">📄 서류 · 절차 안내</span>
            <span className="header-badge">🕒 24시간 상담 가능</span>
          </div>
        </div>

        {/* 오른쪽: 말풍선 + 캐릭터 비주얼 영역 */}
        <div className="header-visual">
          <div className="header-speech-bubble">
            <p className="bubble-greet">안녕하세요!</p>
            <p className="bubble-main">궁금한 정보를 쉽고 빠르게</p>
            <p className="bubble-highlight">안내해드릴게요.</p>
  
          </div>
          <img src={gouni} alt="인사하는 고우니" className="header-gouni" />
        </div>
      </div>
    </header>
  );
}

export default Header;