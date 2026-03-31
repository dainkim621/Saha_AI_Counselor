from sqlalchemy import Column, Integer, Text, Date
from pgvector.sqlalchemy import Vector
from .database import Base

class Notice(Base):
    __tablename__ = "notices"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(Text, nullable=False)
    content = Column(Text)
    url = Column(Text)
    created_at = Column(Date)
    # AI 검색을 위한 벡터값 저장 칸 (1536차원)
    embedding = Column(Vector(1536))