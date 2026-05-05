import gouni from "../assets/gouni.png";

function MascotCard() {
  return (
    <div className="mascot-card">
      <img
        src={gouni}
        alt="사하구 캐릭터 고우니"
        className="mascot-image"
      />

      <h2>고우니 챗봇</h2>
      <p>사하구 민원 정보를 쉽고 친절하게 안내해드릴게요.</p>
    </div>
  );
}

export default MascotCard;