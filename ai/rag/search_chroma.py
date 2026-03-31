import os
import re
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

PERSIST_DIR = "data/vector/chroma_db"
MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

TOP_K = 5

HIGHLIGHT_KEYWORDS = [
    "전입", "전입신고", "주민등록", "민원", "신청", "구비서류",
    "처리기간", "수수료", "문의처", "신고기한", "신청방법",
    "방문", "온라인", "처리절차", "제출서류", "발급", "복지"
]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_query(query: str) -> list[str]:
    """
    질문 확장
    - 전입신고 관련 표현을 더 넓게 검색해보기 위함
    """
    expanded = [query]

    q = query.replace(" ", "")
    if "전입신고" in q or "전입" in q or "주소이전" in q or "이사" in q:
        expanded.extend([
            "전입신고 방법",
            "주민등록 전입신고",
            "주소 이전 신고",
            "이사 후 전입신고",
        ])

    # 중복 제거
    result = []
    seen = set()
    for item in expanded:
        item = item.strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)

    return result


def count_keyword_hits(text: str) -> int:
    merged = clean_text(text)
    return sum(1 for kw in HIGHLIGHT_KEYWORDS if kw in merged)


def shorten_text(text: str, limit: int = 450) -> str:
    text = clean_text(text)
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


def print_result(i: int, doc, score: float):
    title = doc.metadata.get("title", "")
    section = doc.metadata.get("section", "")
    url = doc.metadata.get("url", "")
    chunk_id = doc.metadata.get("chunk_id", "")
    chunk_index = doc.metadata.get("chunk_index", "")
    length = doc.metadata.get("length", "")
    content = doc.page_content

    keyword_hits = count_keyword_hits(f"{title}\n{section}\n{content}")

    print("\n" + "-" * 100)
    print(f"[{i}] score={score:.4f} | keyword_hits={keyword_hits}")
    print(f"제목: {title}")
    print(f"섹션: {section}")
    print(f"URL: {url}")
    print(f"chunk_id: {chunk_id}")
    print(f"chunk_index: {chunk_index}")
    print(f"length: {length}")
    print("내용 미리보기:")
    print(shorten_text(content, 500))


def search_with_fallback(vectordb, query: str, k: int = TOP_K):
    """
    1차: 원문 질문 검색
    2차: 질문 확장 검색
    중복 chunk_id 제거 후 상위 결과 반환
    """
    query_candidates = normalize_query(query)

    all_results = []
    seen_chunk_ids = set()

    for q in query_candidates:
        results = vectordb.similarity_search_with_score(q, k=k)

        for doc, score in results:
            chunk_id = doc.metadata.get("chunk_id", "")
            dedup_key = chunk_id or f"{doc.metadata.get('title', '')}-{doc.metadata.get('chunk_index', '')}"

            if dedup_key in seen_chunk_ids:
                continue

            seen_chunk_ids.add(dedup_key)
            all_results.append((doc, score, q))

    # score 오름차순 정렬
    all_results.sort(key=lambda x: x[1])

    return all_results[:k]


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

    print("\n검색 테스트 시작")
    print("종료하려면 exit 입력")

    while True:
        query = input("\n질문 입력 (종료: exit): ").strip()
        if query.lower() == "exit":
            print("검색 종료")
            break

        if not query:
            print("질문을 입력하세요.")
            continue

        results = search_with_fallback(vectordb, query, k=TOP_K)

        print("\n검색 결과")
        print("=" * 100)
        print("질문:", query)
        print("확장 질의:", " | ".join(normalize_query(query)))

        if not results:
            print("검색 결과가 없습니다.")
            continue

        for i, (doc, score, matched_query) in enumerate(results, start=1):
            print_result(i, doc, score)
            print(f"매칭 질의: {matched_query}")

        print("\n" + "=" * 100)
        print("판단 기준")
        print("- 제목/섹션에 질문 핵심어가 들어있는지 확인")
        print("- 상위 3개가 같은 주제(예: 전입신고)로 모이는지 확인")
        print("- unrelated 문서가 상위에 뜨면 crawler/preprocess 품질 문제일 가능성이 큼")


if __name__ == "__main__":
    main()