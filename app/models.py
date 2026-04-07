# app/models.py
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from .database import Base

class Notice(Base):
    __tablename__ = "notices"

    # 기본 정보
    id = Column(Integer, primary_key=True, index=True)
    doc_id = Column(String, unique=True, index=True)  # 친구가 만든 해시값 (중복 방지)
    
    # 크롤링 데이터
    url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    content = Column(Text, nullable=False)  # 전체 본문 (text 필드)
    source = Column(String, default="saha.go.kr")
    
    # 메타데이터 (있으면 좋고 없으면 일단 비워둘 것)
    author = Column(String, nullable=True)  # 담당부서
    published_at = Column(String, nullable=True) # 작성일 (문자열로 우선 저장)
    
    # 관리용 데이터
    created_at = Column(DateTime(timezone=True), server_default=func.now()) # DB에 들어온 시각