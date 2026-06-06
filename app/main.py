from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import engine, get_db
from . import models
from .api import chat  # 기존 챗봇 라우터
from .models import Notice
from pydantic import BaseModel
from app.services.chat_service import ask_saha_ai

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="사하구 AI 상담사 API")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 배포시에는 ["http://localhost:3000"] 처럼 특정 주소만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

#DB 테이블 생성 (이미 생성했지만 안전하게 유지)
models.Base.metadata.create_all(bind=engine)



#Pydantic 모델 (API 응답 규격)
#서버가 사용자에게 결과를 돌려줄 때의 규격 
# db에서 찾은 공지사항 정보를 줄 때 id, title, author 등의 형식에 맞춰서 줌
class NoticeResponse(BaseModel): 
    id: int
    doc_id: str
    title: str
    author: str | None
    published_at: str | None
    views: int | None
    source: str | None

    class Config:
        from_attributes = True
        
# 💡 1. 프론트엔드가 보낼 JSON 바디 규격을 정의하는 Pydantic 모델
# 웅변 형식: { "role": "user", "content": "..." }
class ChatMessage(BaseModel):
    role: str
    content: str
    
#요청 데이터를 담을 규격 정의
#사용자가 서버에 보내는 데이터의 규격/ 나한테 질문 할때는 question을 담아서 보내야됨. 
# 웅변 형식: { "question": "...", "history": [...] }
class ChatRequest(BaseModel):
    question: str
    history: List[ChatMessage] = []  # 기본값은 빈 리스트

# 3. 기존 챗봇 라우터 등록
app.include_router(chat.router, prefix="/chat", tags=["Chat"])

# 4. 공지사항 조회 API 엔드포인트
@app.get("/notices", response_model=List[NoticeResponse], tags=["Notices"])
def read_notices(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """DB에 저장된 공지사항 목록을 가져옵니다."""
    notices = db.query(Notice).offset(skip).limit(limit).all()
    return notices

@app.get("/notices/{notice_id}", response_model=NoticeResponse, tags=["Notices"])
def read_notice(notice_id: int, db: Session = Depends(get_db)):
    """특정 ID의 공지사항 상세 내용을 가져옵니다."""
    notice = db.query(Notice).filter(Notice.id == notice_id).first()
    if not notice:
        raise HTTPException(status_code=404, detail="공지사항을 찾을 수 없습니다.")
    return notice

from sqlalchemy import desc

@app.get("/notices/search", tags=["Notices"])
def search_notices(
    q: str = None, 
    sort_by: str = "date",  # "date" 또는 "views"
    db: Session = Depends(get_db)
):
    query = db.query(Notice)
    
    # 1. 키워드 검색 (제목 또는 본문에 포함된 경우)
    if q:
        query = query.filter(Notice.title.contains(q) | Notice.text.contains(q))
    
    # 2. 정렬 로직
    if sort_by == "views":
        query = query.order_by(desc(Notice.views))
    else:
        query = query.order_by(desc(Notice.published_at))
        
    results = query.all()
    
    if not results:
        raise HTTPException(status_code=404, detail=f"'{q}'에 대한 검색 결과가 없습니다.")
        
    return results

@app.get("/", tags=["Root"])
def root():
    return {"status": "Saha AI Server is running!", "version": "1.0.0"}

#챗봇 api 엔드포인트 
@app.post("/ai-chat", tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    try:
        user_question = request.question
        
        # 💡 [버그 교정] 반복문 변수명을 msg로 변경하여 모듈 이름(chat)과의 충돌을 방지합니다.
        raw_history = [
            {"role": msg.role, "content": msg.content} 
            for msg in request.history
        ]
        
        # 개조해 둔 ask_saha_ai 함수에 '현재 질문'과 '과거 이력'을 함께 토스합니다!
        answer = ask_saha_ai(user_question=user_question, history=raw_history)
        
        # 프론트엔드 App.tsx 규격(data.answer)에 맞춰 응답을 반환합니다.
        return {"question": user_question, "answer": answer}

    except Exception as e:
        print(f"🔥 백엔드 에러 발생: {e}")
        raise HTTPException(status_code=500, detail=str(e))
