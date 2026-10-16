
import gouni from "../assets/gouni.png";

type HeaderProps = {
  // 이용 가이드 버튼을 눌렀을 때 실행할 함수
  onGuideClick: () => void;
};

function Header({ onGuideClick }: HeaderProps) {
  return (
    <header className="header">
      <div className="header-content">

        {/* 왼쪽: 서비스 제목 및 설명 */}
        <div className="header-text">
          <h1>사하구 AI 민원 상담사</h1>

          <p className="header-description">
            민원 신청 방법과 필요한 서류를 안내해 드립니다.
          </p>

          {/* 이용 가이드 버튼 */}
          <button
            type="button"
            className="header-guide-button"
            onClick={onGuideClick}
          >
            이용 가이드
          </button>
        </div>

        {/* 오른쪽: 사하구 마스코트 고우니 */}
        <div className="header-visual">
          <img
            src={gouni}
            alt="사하구 마스코트 고우니"
            className="header-gouni"
          />
        </div>

      </div>
    </header>
  );
}

export default Header;
