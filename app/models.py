from sqlalchemy import Column, Integer, String, Text, DateTime, JSON
from pgvector.sqlalchemy import Vector  # 추가
from sqlalchemy.sql import func
from app.database import Base

class Notice(Base):
    __tablename__ = "notices"

    #고유 식별자 (청크 단위 관리를 위해 수정)
    # 기존 id 대신 JSONL에 있는 chunk_id를 PK로 쓰거나, 별도 PK를 둡니다.
    id = Column(Integer, primary_key=True, index=True) 
    chunk_id = Column(String, unique=True, index=True, nullable=False) # 예: doc_id_0
    doc_id = Column(String, index=True, nullable=False)               # 원본 문서 ID
    
    # 2. 메타데이터 (검색 및 필터링용)
    url = Column(String, nullable=False)
    source = Column(String, default="saha.go.kr")
    title = Column(String, nullable=False)
    author = Column(String) 
    published_at = Column(String, nullable=True)  #탈짜 통합 컬럼
    views = Column(Integer, default=0)
    
    menu_path = Column(JSON)       # ['전자민원', '사하구에 바란다'] 형태 저장
    page_type = Column(String, nullable=True)     # 'contents' 또는 'civil_form_guide' 구분용
    
    major = Column(String, nullable=True)                             # 대분류 (예: 증명민원 통합발급)
    minor = Column(String, nullable=True)                             # 중분류 (예: 인감증명발급)
    context = Column(Text, nullable=True)
    
    # 3. 데이터 본체 (가장 중요!)
    chunk_text = Column(Text, nullable=False) # AI가 읽을 핵심 텍스트
    chunk_index = Column(Integer)             # 문서 내 몇 번째 조각인지
    # full_text = Column(Text, nullable=True)   # (선택) 필요한 경우 원문 전체 저장

    # 4. 시스템 날짜
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # 5. 벡터 검색 위한 컬럼 (1536차원)
    embedding = Column(Vector(1536))