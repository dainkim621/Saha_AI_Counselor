import gouni from "../assets/gouni.png";

function MascotCard() {
  return (
    <div className="mascot-card">
      <div className="mascot-glow">
        <img
          src={gouni}
          alt="사하구 캐릭터 고우니"
          className="gouni-main"
        />
      </div>

      <div className="mascot-text">
        <span className="mascot-label">사하구 AI 챗봇</span>
        <h2>고우니</h2>
        <p>
          필요한 민원 정보를 찾기 쉽게 정리해서 안내해드릴게요.
        </p>
      </div>
    </div>
  );
}

export default MascotCard;