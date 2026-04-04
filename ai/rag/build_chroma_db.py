import os
import re
import json
import shutil
import hashlib

from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

INPUT_FILE = "data/processed/saha_chunks.jsonl"
PERSIST_DIR = "data/vector/chroma_db"

MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

MIN_TEXT_LEN = 60

NOISY_KEYWORDS = [
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
    "이전글",
    "다음글",
    "목록",
    "공유",
    "프린트",
    "만족도 조사",
    "페이지 만족도",
]

MENU_SIGNALS = [
    "주메뉴",
    "전자민원",
    "정보공개",
    "분야별 정보",
    "사하구 홈페이지",
    "비주얼 홍보 이미지",
    "이전 이미지",
    "다음 이미지",
]

CIVIL_KEYWORDS = [
    "전입", "전입신고", "민원", "주민등록", "신청", "구비서류",
    "처리기간", "수수료", "문의처", "신고기한", "신청방법",
    "방문", "온라인", "처리절차", "제출서류", "발급", "복지"
]


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def clean_inline_text(text: str) -> str:
    text = clean_text(text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def normalize_for_dedup(text: str) -> str:
    """
    중복 판별용 정규화
    """
    text = clean_inline_text(text).lower()
    text = re.sub(r"\[문서제목\]\s*", "", text)
    text = re.sub(r"\[섹션\]\s*", "", text)
    text = re.sub(r"제목:\s*", "", text)
    text = re.sub(r"섹션:\s*", "", text)
    text = re.sub(r"본문:\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_text_hash(text: str) -> str:
    normalized = normalize_for_dedup(text)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def is_noisy_text(text: str, title: str = "", section: str = "") -> bool:
    merged = f"{title}\n{section}\n{text}"
    merged_inline = clean_inline_text(merged)

    if len(merged_inline) < MIN_TEXT_LEN:
        return True

    noisy_hit = sum(1 for kw in NOISY_KEYWORDS if kw in merged_inline)
    menu_hit = sum(1 for kw in MENU_SIGNALS if kw in merged_inline)
    civil_hit = sum(1 for kw in CIVIL_KEYWORDS if kw in merged_inline)

    if noisy_hit >= 2:
        return True

    if menu_hit >= 2 and civil_hit == 0:
        return True

    lines = [line.strip() for line in merged.splitlines() if line.strip()]
    if lines:
        short_lines = sum(1 for line in lines if len(line) <= 10)
        if short_lines / len(lines) > 0.5 and civil_hit == 0:
            return True

    return False


def build_embedding_text(title: str, section: str, chunk_text: str) -> str:
    """
    제목 + 섹션 + 본문을 함께 임베딩해서 검색 품질 개선
    """
    parts = []

    if title:
        parts.append(f"제목: {title}")

    if section and section != "일반":
        parts.append(f"섹션: {section}")

    parts.append(f"본문: {chunk_text}")

    return "\n".join(parts).strip()


def load_chunks(file_path):
    docs = []
    seen_hashes = set()

    total_lines = 0
    skipped_json = 0
    skipped_empty = 0
    skipped_noise = 0
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
            title = clean_inline_text(item.get("title", ""))
            section = clean_inline_text(item.get("section", ""))
            url = clean_inline_text(item.get("url", ""))

            if not chunk_text:
                skipped_empty += 1
                continue

            if is_noisy_text(chunk_text, title, section):
                skipped_noise += 1
                continue

            combined_text = build_embedding_text(title, section, chunk_text)
            text_hash = make_text_hash(combined_text)

            # 중복 제거
            if text_hash in seen_hashes:
                skipped_dup += 1
                continue
            seen_hashes.add(text_hash)

            metadata = {
                "chunk_id": item.get("chunk_id"),
                "doc_id": item.get("doc_id"),
                "title": title,
                "section": section,
                "url": url,
                "source": item.get("source"),
                "chunk_index": item.get("chunk_index"),
                "section_chunk_index": item.get("section_chunk_index"),
                "length": item.get("length"),
            }

            docs.append(Document(page_content=combined_text, metadata=metadata))

    print(f"[로딩 완료] 전체 라인 수: {total_lines}")
    print(f"[로딩 완료] JSON 스킵: {skipped_json}")
    print(f"[로딩 완료] 빈 텍스트 스킵: {skipped_empty}")
    print(f"[로딩 완료] 노이즈 스킵: {skipped_noise}")
    print(f"[로딩 완료] 중복 스킵: {skipped_dup}")
    print(f"[로딩 완료] 최종 문서 수: {len(docs)}")

    return docs


def reset_chroma_dir(path: str):
    if os.path.exists(path):
        shutil.rmtree(path)
    os.makedirs(path, exist_ok=True)


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