from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..services import search_service

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/chat")
def chat_with_ai(question: str, db: Session = Depends(get_db)):
    # 1. 여기서 질문을 벡터로 변환 (AI 담당 친구랑 합칠 부분)
    # 2. search_service를 이용해 DB 검색
    # 3. ai_service를 이용해 답변 생성
    return {"message": "곧 인공지능 답변이 완성될 거예요!"}