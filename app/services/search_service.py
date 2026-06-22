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

def reciprocal_rank_fusion(vector_results, keyword_results, k=60):
    """벡터 검색 순위와 키워드 검색 순위를 합산(RRF)하는 함수"""
    rrf_score = {}

    # 1. 벡터 검색 순위 매기기
    for rank, doc in enumerate(vector_results):
        if doc.id not in rrf_score:
            rrf_score[doc.id] = {"doc": doc, "score": 0.0}
        rrf_score[doc.id]["score"] += 1.0 / (k + (rank + 1))

    # 2. 키워드 검색 순위 매기기 및 합산
    for rank, doc in enumerate(keyword_results):
        if doc.id not in rrf_score:
            rrf_score[doc.id] = {"doc": doc, "score": 0.0}
        rrf_score[doc.id]["score"] += 1.0 / (k + (rank + 1))

    # 점수 높은 순으로 정렬
    sorted_docs = sorted(rrf_score.values(), key=lambda x: x["score"], reverse=True)
    return [item["doc"] for item in sorted_docs]

def get_similar_chunks(query: str, top_k: int = 5): # k값을 조금 늘려주면 더 정확해짐. but 토큰이 늘어나서 비용이 증가할 수 있음.
    db: Session = SessionLocal()
    
    # 1. 사용자의 질문을 벡터로 변환
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    # 2-1. 벡터 유사도 기반 검색 상위 5개
    vector_results = db.query(Notice).order_by(
        Notice.embedding.cosine_distance(query_embedding)
    ).limit(top_k).all()
    
    # 2-2. 키워드 검색 상위 5개
    keyword_terms = " & ".join([term for term in query.split() if term])
    keyword_results = []
    if keyword_terms:
        try:
            keyword_results = db.query(Notice).filter(
                Notice.chunk_text.match(keyword_terms) # chunk_text 또는 content 컬럼 매칭
            ).limit(top_k).all()
        except Exception as e:
            print(f"키워드 검색 실패(기본 벡터 검색만 활용): {e}")
            keyword_results = []
            
    # 3. RRF 알고리즘으로 두 검색 결과 하이브리드 병합
    hybrid_results = reciprocal_rank_fusion(vector_results, keyword_results)
    
    
    print(f"🔍 [하이브리드 검색 완료] 최종 합산된 문서 수: {len(hybrid_results)}개")
    if hybrid_results:
        print(f"DEBUG: 1등 문서 제목 -> {hybrid_results[0].title}")
    else:
        print("DEBUG: ❌ 검색 결과가 없습니다!")

    db.close()
    return hybrid_results[:top_k] # 최종적으로 상위 top_k개만 슬라이싱해서 리턴

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
    test_query = "장학금 신청 기간 알려줘"
    chunks = get_similar_chunks(test_query)
    
    print(f" 질문: {test_query}")
    for i, chunk in enumerate(chunks):
        print(f"[{i+1}] 유사도 점수 기반 추출: {chunk.title} - {chunk.chunk_text[:50]}...")