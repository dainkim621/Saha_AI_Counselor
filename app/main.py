from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from .database import engine, get_db
from . import models
from .api import chat  # 기존 챗봇 라우터
from .models import Notice
from pydantic import BaseModel

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

# 1. DB 테이블 생성 (이미 생성했지만 안전하게 유지)
models.Base.metadata.create_all(bind=engine)



# 2. Pydantic 모델 (API 응답 규격)
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