function App() {
  return (
    <div style={{ padding: "20px", fontFamily: "Arial" }}>
      
      <h1>🏢 사하구 AI 민원 상담 챗봇</h1>

      {/* 채팅 출력 영역 */}
      <div style={{
        border: "1px solid #ccc",
        height: "400px",
        padding: "10px",
        marginBottom: "10px",
        overflowY: "scroll"
      }}>
        <p><b>AI:</b> 안녕하세요! 무엇을 도와드릴까요?</p>
      </div>

      {/* 입력창 */}
      <div>
        <input 
          type="text" 
          placeholder="질문을 입력하세요..."
          style={{ width: "80%", padding: "10px" }}
        />
        <button style={{ padding: "10px" }}>전송</button>
      </div>

    </div>
  );
}

export default App;