from openai import OpenAI
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Notice
import os
from dotenv import load_dotenv
import math

# openAI API 키
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)


def calculate_cosine_similarity(v1, v2):
    """두 벡터(숫자 리스트)의 코사인 유사도를 구하는 수학 공식"""
    dot_product = sum(a * b for a, b in zip(v1, v2))
    norm_a = math.sqrt(sum(a * a for a in v1))
    norm_b = math.sqrt(sum(b * b for b in v2))
    if not norm_a or not norm_b:
        return 0.0
    return dot_product / (norm_a * norm_b)

def reciprocal_rank_fusion(vector_results, keyword_results, k=60, metadata_results=None):
    rrf_scores = {}
    doc_map = {}

    # 기존 벡터 검색 + 키워드 검색 유지
    # 메타데이터 검색 결과도 RRF에 참여
    result_lists = [vector_results, keyword_results]

    if metadata_results:
        result_lists.append(metadata_results)

    for results in result_lists:
        for rank, doc in enumerate(results, start=1):
            doc_id = doc.id

            if doc_id not in rrf_scores:
                rrf_scores[doc_id] = 0
                doc_map[doc_id] = doc

            rrf_scores[doc_id] += 1 / (k + rank)

    sorted_ids = sorted(
        rrf_scores,
        key=lambda doc_id: rrf_scores[doc_id],
        reverse=True
    )

    return [doc_map[doc_id] for doc_id in sorted_ids]


def get_similar_chunks(query: str, top_k: int = 3): # k값을 조금 늘려주면 더 정확해짐. but 토큰이 늘어나서 비용이 증가할 수 있음.
    db: Session = SessionLocal()

    # 1. 쿼리 벡터화
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

    # 3. 메타데이터 검색 추가
    # 제목(title), 메뉴 경로(menu_path), 문서 유형(page_type) 활용
    from sqlalchemy import or_, cast, Text, case

    metadata_results = []

    try:
        search_terms = [
            term for term in query.split()
            if len(term) >= 2
        ]

        if search_terms:
            metadata_conditions = []
            score_conditions = []

            for term in search_terms:
                keyword = f"%{term}%"

                title_match = Notice.title.ilike(keyword)
                menu_match = cast(Notice.menu_path, Text).ilike(keyword)
                type_match = Notice.page_type.ilike(keyword)

                # 하나라도 일치하면 검색 후보에 포함
                metadata_conditions.extend([
                    title_match,
                    menu_match,
                    type_match
                ])

                # 일치하는 단어가 많을수록 높은 점수
                # 제목 일치에 더 높은 가중치 부여
                score_conditions.extend([
                    case((title_match, 3), else_=0),
                    case((menu_match, 2), else_=0),
                    case((type_match, 1), else_=0)
                ])

            metadata_score = sum(score_conditions)

            metadata_results = (
                db.query(Notice)
                .filter(or_(*metadata_conditions))
                .order_by(
                    metadata_score.desc(),
                    Notice.id.asc()
                )
                .limit(max(top_k, 10))
                .all()
            )

    except Exception as e:
        print(f"메타데이터 검색 실패: {e}")
        db.rollback()
        metadata_results = []

    # 4. 벡터 + 키워드 + 메타데이터 검색 결과를 RRF로 통합
    hybrid_results = reciprocal_rank_fusion(
        vector_results,
        keyword_results,
        metadata_results=metadata_results
    )

    print(f"📂 [메타데이터 검색] {len(metadata_results)}개 문서 검색")
    print(f"🔍 [RRF 통합] 총 {len(hybrid_results)}개 후보 문서")


    # 4. 최종 상위 3개 문서와 질문 벡터의 유사도 뽑기
    final_output = []

    for doc in hybrid_results[:top_k]:

        # 1단계에서 구해둔 query_embedding과
        # DB에 저장되어 있던 doc.embedding을 비교
        if hasattr(doc, 'embedding') and doc.embedding is not None:

            # 0.0 ~ 1.0 사이로 나오는 유사도 값을
            # % 형식(0 ~ 100)으로 변환
            raw_sim = calculate_cosine_similarity(
                query_embedding,
                doc.embedding
            )

            min_score = 0.28
            max_score = 0.55

            if raw_sim <= min_score:
                adjusted_sim = 0.0

            elif raw_sim >= max_score:
                adjusted_sim = 100.0

            else:
                adjusted_sim = (
                    (raw_sim - min_score)
                    / (max_score - min_score)
                ) * 100

            doc.score = int(round(adjusted_sim, 1))

        else: # 혹시라도 벡터 값이 없는 문서라면 안정적으로 기본값 넣음
            doc.score = 0.0

        final_output = [
            doc for doc in final_output
            if doc.score >= 10.0
        ]

        final_output.append(doc)

    print(
        f"🔍 [하이브리드 검색 완료] "
        f"최종 합산된 문서 수: {len(final_output)}개"
    )

    if final_output:
        print(
            f"DEBUG: 1등 문서 제목 -> "
            f"{final_output[0].title}, "
            f"유사도: {final_output[0].score}%"
        )
    else:
        print("DEBUG: ❌ 검색 결과가 없습니다!")

    db.close()

    return final_output, query_embedding

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

# # 테스트용 코드
# if __name__ == "__main__":
#     test_query = "장학금 신청 기간 알려줘"
#     chunks, query_embedding = get_similar_chunks(test_query)
    
#     print(f" 질문: {test_query}")
#     for i, chunk in enumerate(chunks):
#         print(f"[{i+1}] 유사도 점수 기반 추출: {chunk.title} - {chunk.chunk_text[:50]}...")