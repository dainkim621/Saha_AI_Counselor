import os
import json
import shutil

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

INPUT_FILE = "data/processed/saha_chunks.jsonl"
PERSIST_DIR = "data/vector/chroma_db"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


def load_chunks(file_path):
    docs = []
    seen_texts = set()

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"[SKIP] JSON 파싱 실패: line {line_num}")
                continue

            chunk_text = item.get("chunk_text", "").strip()
            title = item.get("title", "").strip()
            url = item.get("url", "").strip()

            if not chunk_text:
                continue

            if is_noisy_text(chunk_text):
                continue

            combined_text = build_embedding_text(title, chunk_text)

            # 완전 중복 제거
            if combined_text in seen_texts:
                continue
            seen_texts.add(combined_text)

            metadata = {
                "chunk_id": item.get("chunk_id"),
                "doc_id": item.get("doc_id"),
                "title": title,
                "url": url,
                "source": item.get("source"),
                "chunk_index": item.get("chunk_index"),
                "length": item.get("length"),
            }

            docs.append(Document(page_content=combined_text, metadata=metadata))

    return docs


def build_embedding_text(title: str, chunk_text: str) -> str:
    """
    제목 + 본문을 함께 임베딩해서 검색 품질 개선
    """
    if title:
        return f"제목: {title}\n본문: {chunk_text}"
    return chunk_text


def is_noisy_text(text: str) -> bool:
    """
    메뉴, 네비게이션, 푸터 같은 잡텍스트 제거용
    """
    if len(text) < 40:
        return True

    noisy_keywords = [
        "본문 바로가기",
        "주메뉴 바로가기",
        "하단 바로가기",
        "홈",
        "로그인",
        "사이트맵",
        "개인정보처리방침",
        "저작권보호정책",
        "행정전화번호",
        "뷰어다운로드",
    ]

    hit_count = sum(1 for kw in noisy_keywords if kw in text)

    if hit_count >= 2:
        return True

    # 특수문자/짧은 토막 반복 제거
    stripped = text.replace(" ", "")
    if len(stripped) < 20:
        return True

    return False


def reset_chroma_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


def main():
    print("[1] 기존 Chroma DB 초기화 중...")
    reset_chroma_dir(PERSIST_DIR)

    print("[2] chunk 로딩 중...")
    documents = load_chunks(INPUT_FILE)

    print(f"총 문서 수: {len(documents)}")

    if not documents:
        print("저장할 문서가 없습니다. saha_chunks.jsonl 내용을 확인하세요.")
        return

    print("[3] 임베딩 모델 로드 중...")
    embedding = HuggingFaceEmbeddings(model_name=MODEL_NAME)

    print("[4] Chroma DB 생성 중...")
    vectordb = Chroma.from_documents(
        documents=documents,
        embedding=embedding,
        persist_directory=PERSIST_DIR
    )

    vectordb.persist()

    print("\nChroma DB 구축 완료")
    print(f"저장 위치: {PERSIST_DIR}")
    print(f"저장된 문서 수: {len(documents)}")


if __name__ == "__main__":
    main()