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

def get_similar_chunks(query: str, top_k: int = 5): # k값을 조금 늘려주면 더 정확해집니다.
    db: Session = SessionLocal()
    
    # 1. 사용자의 질문을 벡터로 변환
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    # 2. 필터링(threshold) 없이 일단 가장 가까운 top_k개를 가져옵니다.
    results = db.query(Notice).order_by(
        Notice.embedding.cosine_distance(query_embedding)
    ).limit(top_k).all()
    
    # 디버깅: 실제 검색된 본문이 있는지 확인
    print(f"DEBUG: 검색된 제목들 -> {[r.title for r in results]}")
    if results:
        print(f"DEBUG: 첫 번째 검색결과 본문 -> {results[0].chunk_text[:50]}...")
    else:
        print("DEBUG: ❌ 검색 결과가 하나도 없습니다!")

    db.close()
    return results

def search_notices(query_embedding, db):
    # 유사도 임계값(Threshold) 설정 
    # 0에 가까울수록 정답에 가깝고, 1에 가까울수록 먼 내용
    threshold = 0.7

    results = db.query(Notice).filter(
        Notice.embedding.cosine_distance(query_embedding) < threshold
    ).order_by(
        Notice.embedding.cosine_distance(query_embedding)
    ).limit(3).all()
    
    return results
# 테스트용 코드
if __name__ == "__main__":
    test_query = "가구원 수가 1인일 때 수급자로 선정되려면 기준 중위 소득이 얼마여야돼?"
    chunks = get_similar_chunks(test_query)
    
    print(f"🔍 질문: {test_query}")
    for i, chunk in enumerate(chunks):
        print(f"[{i+1}] 유사도 점수 기반 추출: {chunk.title} - {chunk.chunk_text[:50]}...")