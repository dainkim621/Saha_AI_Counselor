from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Notice
import os
from dotenv import load_dotenv

# openAI API 키
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def get_similar_chunks(query: str, top_k: int = 3):
    db: Session = SessionLocal()
    
    # 1. 사용자의 질문을 벡터로 변환
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    # 2. pgvector의 <-> (L2 distance) 또는 <=> (Cosine distance) 연산자로 유사도 검색
    # 여기서는 코사인 유사도 거리를 기준으로 정렬합니다.
    results = db.query(Notice).order_by(
        Notice.embedding.cosine_distance(query_embedding)
    ).limit(top_k).all()
    print(f"DEBUG: 검색된 제목들 -> {[r.title for r in results]}")
    
    db.close()
    return results

# 테스트용 코드
if __name__ == "__main__":
    test_query = "장학금 신청 기간 알려줘"
    chunks = get_similar_chunks(test_query)
    
    print(f"🔍 질문: {test_query}")
    for i, chunk in enumerate(chunks):
        print(f"[{i+1}] 유사도 점수 기반 추출: {chunk.title} - {chunk.chunk_text[:50]}...")