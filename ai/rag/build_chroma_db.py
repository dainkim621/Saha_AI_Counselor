import os
import re
import json
import shutil
import hashlib

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

# ==============================
# 설정
# ==============================
INPUT_FILE = "data/processed/saha_chunks.jsonl"
PERSIST_DIR = "data/vector/chroma_db"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

# 너무 짧은 chunk는 검색 가치가 낮아서 제외
MIN_TEXT_LEN = 60


# ==============================
# 텍스트 정리 유틸
# ==============================
def clean_text(text: str) -> str:
    """
    줄바꿈 구조는 유지하면서 기본 정리
    """
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def clean_inline_text(text: str) -> str:
    """
    한 줄 비교/중복 체크용 정리
    """
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_dedup(text: str) -> str:
    """
    중복 판별용 정규화
    - 제목/메뉴경로/링크문맥/페이지유형 같은 prefix 차이보다
      실제 본문이 같은지를 더 잘 보기 위해 일부 라벨 제거
    """
    text = clean_inline_text(text).lower()

    text = re.sub(r"제목:\s*", "", text)
    text = re.sub(r"메뉴경로:\s*", "", text)
    text = re.sub(r"링크문맥:\s*", "", text)
    text = re.sub(r"페이지유형:\s*", "", text)
    text = re.sub(r"작성자:\s*", "", text)
    text = re.sub(r"날짜:\s*", "", text)
    text = re.sub(r"조회수:\s*", "", text)
    text = re.sub(r"본문:\s*", "", text)

    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_text_hash(text: str) -> str:
    normalized = normalize_for_dedup(text)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


# ==============================
# 노이즈 판별
# ==============================
def is_menu_like_text(text: str) -> bool:
    """
    크롤러/전처리 단계에서 이미 많이 걸렀지만,
    벡터DB 저장 직전에 한 번 더 방어적으로 체크
    """
    text = clean_text(text)
    if not text:
        return True

    menu_signals = [
        "주메뉴", "사하구 홈페이지", "만족도 조사", "개인정보처리방침",
        "저작권", "공유", "프린트", "이전글", "다음글", "목록"
    ]

    hit = sum(1 for x in menu_signals if x in text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    short_lines = sum(1 for line in lines if len(line) <= 10)

    if hit >= 2:
        return True

    if lines and short_lines / len(lines) > 0.65:
        return True

    return False


def is_noisy_chunk(chunk_text: str, title: str = "", menu_path=None, anchor_text: str = "") -> bool:
    """
    키워드 하드코딩보다,
    '검색 가치가 있는 chunk인가'를 최소 기준으로 판별
    """
    menu_path = menu_path or []
    merged = "\n".join([
        title or "",
        " > ".join(menu_path),
        anchor_text or "",
        chunk_text or "",
    ])
    merged_inline = clean_inline_text(merged)

    if len(merged_inline) < MIN_TEXT_LEN:
        return True

    if is_menu_like_text(merged):
        return True

    return False


# ==============================
# 임베딩용 텍스트 구성, 본문 비중을 더 높여서 단순화
# ==============================
def build_embedding_text(
    title: str,
    menu_path,
    anchor_text: str,
    page_type: str,
    chunk_text: str,
    author: str = "",
    date: str = "",
    views=None,
) -> str:
    parts = []

    if title:
        parts.append(f"제목: {title}")

    if menu_path:
        parts.append(f"메뉴경로: {' > '.join(menu_path)}")

    parts.append(f"본문: {chunk_text}")

    return "\n".join(parts).strip()


# ==============================
# chunk 로딩
# ==============================
def load_chunks(file_path: str):
    docs = []
    seen_hashes = set()

    total_lines = 0
    skipped_json = 0
    skipped_empty = 0
    skipped_noisy = 0
    skipped_dup = 0

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, start=1):
            total_lines += 1
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                print(f"[SKIP] JSON 파싱 실패: line {line_num}")
                skipped_json += 1
                continue

            chunk_text = clean_text(item.get("chunk_text", ""))
            title = clean_inline_text(str(item.get("title", "")))
            author = clean_inline_text(str(item.get("author", "")))
            date = clean_inline_text(str(item.get("date", "")))
            url = clean_inline_text(str(item.get("url", "")))
            parent_url = clean_inline_text(str(item.get("parent_url", "")))
            anchor_text = clean_inline_text(str(item.get("anchor_text", "")))
            page_type = clean_inline_text(str(item.get("page_type", "")))
            menu_path = item.get("menu_path", [])
            views = item.get("views", None)

            if not isinstance(menu_path, list):
                menu_path = []

            if not chunk_text:
                skipped_empty += 1
                continue

            if is_noisy_chunk(
                chunk_text=chunk_text,
                title=title,
                menu_path=menu_path,
                anchor_text=anchor_text,
            ):
                skipped_noisy += 1
                continue

            combined_text = build_embedding_text(
                title=title,
                menu_path=menu_path,
                anchor_text=anchor_text,
                page_type=page_type,
                chunk_text=chunk_text,
                author=author,
                date=date,
                views=views,
            )

            text_hash = make_text_hash(combined_text)
            if text_hash in seen_hashes:
                skipped_dup += 1
                continue
            seen_hashes.add(text_hash)

            metadata = {
                "chunk_id": item.get("chunk_id"),
                "doc_id": item.get("doc_id"),
                "title": title,
                "author": author,
                "date": date,
                "views": views,
                "url": url,
                "parent_url": parent_url,
                "anchor_text": anchor_text,
                "menu_path": " > ".join(menu_path),
                "page_type": page_type,
                "source": item.get("source"),
                "chunk_index": item.get("chunk_index"),
            }

            docs.append(
                Document(
                    page_content=combined_text,
                    metadata=metadata
                )
            )

    print(f"[로딩 완료] 전체 라인 수: {total_lines}")
    print(f"[로딩 완료] JSON 스킵: {skipped_json}")
    print(f"[로딩 완료] 빈 텍스트 스킵: {skipped_empty}")
    print(f"[로딩 완료] 메뉴성/노이즈 스킵: {skipped_noisy}")
    print(f"[로딩 완료] 중복 스킵: {skipped_dup}")
    print(f"[로딩 완료] 최종 문서 수: {len(docs)}")

    return docs


# ==============================
# Chroma 초기화
# ==============================
def reset_chroma_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


# ==============================
# 실행
# ==============================
def main():
    if not os.path.exists(INPUT_FILE):
        print(f"입력 파일이 없습니다: {INPUT_FILE}")
        print("먼저 preprocess.py를 실행해서 saha_chunks.jsonl을 생성하세요.")
        return

    print("[1] 기존 Chroma DB 초기화 중...")
    reset_chroma_dir(PERSIST_DIR)

    print("[2] chunk 로딩 중...")
    documents = load_chunks(INPUT_FILE)

    if not documents:
        print("저장할 문서가 없습니다. saha_chunks.jsonl 내용을 확인하세요.")
        return

    print("[3] 임베딩 모델 로드 중...")
    embedding = HuggingFaceEmbeddings(
        model_name=MODEL_NAME,
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True}
    )

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