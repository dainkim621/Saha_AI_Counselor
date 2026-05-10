import gouni from "../assets/gouni.png";

function Header() {
  return (
    <header className="header">
      <div className="header-left">
        <div className="header-icon-box">
          <img src={gouni} alt="고우니" className="header-gouni" />
        </div>

        <div className="header-text">
          <h1>사하구 AI 민원 상담사</h1>
          <p>궁금한 민원 정보를 쉽고 빠르게 안내해드려요.</p>

          <div className="header-badge-list">
            <span className="header-badge">AI 민원 안내</span>
            <span className="header-badge">서류·절차 안내</span>
            <span className="header-badge">24시간 상담 가능</span>
          </div>
        </div>
      </div>
    </header>
  );
}

export default Header;