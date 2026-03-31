from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "Saha-Gu Chatbot Server Running"}

# 나중에 AI 답변 API가 들어갈 자리
@app.post("/chat")
async def ask_ai(question: str):
    return {"answer": f"'{question}'에 대한 답변을 준비 중입니다."}