import os
import re
from typing import List, Tuple

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ==============================
# 설정
# ==============================
PERSIST_DIR = "data/vector/chroma_db"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

TOP_K = 5

# 너무 강한 하드코딩 대신,
# 질의 확장은 "자주 쓰는 민원 표현" 정도만 보조적으로 사용
QUERY_SYNONYMS = {
    "전입신고": ["주민등록 전입신고", "주소 이전 신고", "이사 후 전입신고"],
    "전입": ["전입신고", "주민등록 전입신고"],
    "주소이전": ["주소 이전 신고", "전입신고"],
    "이사": ["이사 후 전입신고", "주소 이전 신고"],
    "등본": ["주민등록등본 발급", "등본 발급"],
    "초본": ["주민등록초본 발급", "초본 발급"],
    "무인민원": ["무인민원발급", "무인민원 발급 안내"],
    "정부24": ["온라인 신청", "정부24 신청"],
}

HIGHLIGHT_KEYWORDS = [
    "전입", "전입신고", "주민등록", "민원", "신청", "구비서류",
    "처리기간", "수수료", "문의처", "신고기한", "신청방법",
    "방문", "온라인", "처리절차", "제출서류", "발급", "정부24",
    "무인민원", "등본", "초본"
]


# ==============================
# 유틸
# ==============================
def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    return text.strip()


def clean_inline_text(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def shorten_text(text: str, limit: int = 420) -> str:
    text = clean_inline_text(text)
    if len(text) <= limit:
        return text
    return text[:limit] + " ..."


def normalize_query(query: str) -> List[str]:
    """
    질문을 조금만 넓혀서 검색.
    너무 많은 하드코딩 확장은 피하고,
    실제 민원 질문에서 자주 바뀌는 표현만 보조적으로 추가.
    """
    query = clean_inline_text(query)
    expanded = [query]

    q_no_space = query.replace(" ", "")

    for key, synonyms in QUERY_SYNONYMS.items():
        if key in query or key in q_no_space:
            expanded.extend(synonyms)

    # 중복 제거
    results = []
    seen = set()
    for item in expanded:
        item = clean_inline_text(item)
        if item and item not in seen:
            seen.add(item)
            results.append(item)

    return results


def count_keyword_hits(text: str) -> int:
    merged = clean_inline_text(text)
    return sum(1 for kw in HIGHLIGHT_KEYWORDS if kw in merged)


def get_metadata(doc, key: str, default=""):
    value = doc.metadata.get(key, default)
    if value is None:
        return default
    return value


def make_dedup_key(doc):
    chunk_id = get_metadata(doc, "chunk_id", "")
    if chunk_id:
        return chunk_id

    title = get_metadata(doc, "title", "")
    chunk_index = get_metadata(doc, "chunk_index", "")
    url = get_metadata(doc, "url", "")
    return f"{title}|{chunk_index}|{url}"

# 같은 문서를 하나로 묶기 위한 key
def make_doc_level_key(doc):
    doc_id = doc.metadata.get("doc_id")
    url = doc.metadata.get("url")

    if doc_id:
        return doc_id

    return url


# ==============================
# 출력
# ==============================
def print_header(title: str):
    line = "=" * 100
    print("\n" + line)
    print(title)
    print(line)


def print_subheader(title: str):
    line = "-" * 100
    print("\n" + line)
    print(title)
    print(line)


def print_kv(label: str, value):
    print(f"{label:<12}: {value}")


def print_result_card(rank: int, doc, score: float, matched_query: str):
    title = get_metadata(doc, "title", "")
    url = get_metadata(doc, "url", "")
    parent_url = get_metadata(doc, "parent_url", "")
    chunk_id = get_metadata(doc, "chunk_id", "")
    chunk_index = get_metadata(doc, "chunk_index", "")
    page_type = get_metadata(doc, "page_type", "")
    anchor_text = get_metadata(doc, "anchor_text", "")
    menu_path = get_metadata(doc, "menu_path", "")
    author = get_metadata(doc, "author", "")
    date = get_metadata(doc, "date", "")
    views = get_metadata(doc, "views", "")
    content = doc.page_content

    keyword_hits = count_keyword_hits(
        f"{title}\n{menu_path}\n{anchor_text}\n{content}"
    )

    print_subheader(f"[{rank}] 검색 결과")
    print_kv("score", f"{score:.4f}")
    print_kv("matched", matched_query)
    print_kv("title", title or "-")
    print_kv("page_type", page_type or "-")
    print_kv("menu_path", menu_path or "-")
    print_kv("anchor_text", anchor_text or "-")
    print_kv("author", author or "-")
    print_kv("date", date or "-")
    print_kv("views", views if views != "" else "-")
    print_kv("keyword_hits", keyword_hits)
    print_kv("chunk_id", chunk_id or "-")
    print_kv("chunk_index", chunk_index if chunk_index != "" else "-")
    print_kv("url", url or "-")
    if parent_url:
        print_kv("parent_url", parent_url)

    print("\n[미리보기]")
    print(shorten_text(content, 500))


def print_summary(query: str, expanded_queries: List[str], results_count: int):
    print_header("검색 요약")
    print_kv("질문", query)
    print_kv("확장 질의", " | ".join(expanded_queries))
    print_kv("결과 수", results_count)


# ==============================
# 검색
# ==============================
def search_with_fallback(vectordb, query: str, k: int = TOP_K):
    query_candidates = normalize_query(query)

    best_doc_results = {}

    for q in query_candidates:
        results = vectordb.similarity_search_with_score(q, k=max(k * 3, 15))

        for doc, score in results:
            doc_key = make_doc_level_key(doc)
            lexical_score = lexical_match_score(query, doc)

            # 제목/메뉴/앵커 중 어디에도 질문이 안 보이면 감점 주는방식 
            semantic_penalty = 0

            if lexical_score == 0:
                semantic_penalty = 0.15
            elif lexical_score == 1:
                semantic_penalty = 0.05

            adjusted_score = score + semantic_penalty




            item = (doc, score, q, lexical_score)

            if doc_key not in best_doc_results:
                best_doc_results[doc_key] = item
            else:
                prev = best_doc_results[doc_key]
                prev_doc, prev_score, prev_q, prev_lexical = prev

                # lexical 점수 우선, 그 다음 semantic score
                if lexical_score > prev_lexical or (
                    lexical_score == prev_lexical and score < prev_score
                ):
                    best_doc_results[doc_key] = item

    all_results = list(best_doc_results.values())

    # lexical 점수 높은 순, semantic score 낮은 순
    all_results.sort(key=lambda x: (-x[3], x[1]))

    return [(doc, score, matched_query) for doc, score, matched_query, _ in all_results[:k]]

# 제목/메뉴경로 일치 검증, 최소 title, menu_path, anchor_text 중 하나에 질문 핵심어가 들어가는 결과만 통과
def normalize_korean_query(text: str) -> str:
    text = clean_inline_text(text)
    text = text.replace(" ", "")
    return text


def lexical_match_score(query: str, doc) -> int:
    """
    제목 / 메뉴경로 / 앵커텍스트 기준으로
    질문과 얼마나 직접 맞는지 점수화
    """
    q = normalize_korean_query(query)

    title = normalize_korean_query(str(doc.metadata.get("title", "")))
    menu_path = normalize_korean_query(str(doc.metadata.get("menu_path", "")))
    anchor_text = normalize_korean_query(str(doc.metadata.get("anchor_text", "")))
    content = normalize_korean_query(doc.page_content[:300])  # 앞부분만 약하게 참고

    score = 0

    if q and q in title:
        score += 5
    if q and q in menu_path:
        score += 4
    if q and q in anchor_text:
        score += 3
    if q and q in content:
        score += 1

    return score


# ==============================
# 실행
# ==============================
def main():
    if not os.path.exists(PERSIST_DIR):
        print(f"Chroma DB 경로가 없습니다: {PERSIST_DIR}")
        print("먼저 build_chroma_db.py를 실행하세요.")
        return

    print("[1] 임베딩 모델 로드 중...")
    embedding = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

    print("[2] Chroma DB 로드 중...")
    vectordb = Chroma(
        persist_directory=PERSIST_DIR,
        embedding_function=embedding
    )

    print_header("Chroma 검색 테스트")
    print("종료하려면 exit 입력")

    while True:
        query = input("\n질문 입력 > ").strip()

        if query.lower() == "exit":
            print("\n검색 종료")
            break

        if not query:
            print("질문을 입력하세요.")
            continue

        expanded_queries = normalize_query(query)
        results = search_with_fallback(vectordb, query, k=TOP_K)

        print_summary(query, expanded_queries, len(results))

        if not results:
            print("\n검색 결과가 없습니다.")
            continue

        for i, (doc, score, matched_query) in enumerate(results, start=1):
            print_result_card(i, doc, score, matched_query)

        print_header("결과 해석 팁")
        print("- score가 낮을수록 보통 더 유사한 결과")
        print("- title / menu_path / anchor_text가 질문 의도와 맞는지 먼저 확인")
        print("- 상위 결과가 같은 민원 주제로 모이면 retrieval 품질이 좋은 편")
        print("- unrelated 문서가 상위에 많으면 crawler / preprocess 품질을 다시 점검")


if __name__ == "__main__":
    main()