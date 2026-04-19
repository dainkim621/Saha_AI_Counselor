import os
import re
import json
from typing import List, Dict

# ==============================
# 설정
# ==============================
INPUT_JSONL = "data/raw/saha_docs.jsonl"
OUTPUT_DIR = "data/processed"
OUTPUT_JSONL = os.path.join(OUTPUT_DIR, "saha_chunks.jsonl")

MIN_CHUNK_LEN = 50
MAX_CHUNK_LEN = 700
OVERLAP = 120

SECTION_HINTS = [
    "신청대상", "신청방법", "처리절차", "처리기간", "수수료",
    "구비서류", "제출서류", "유의사항", "문의처", "신고기한",
    "온라인 신청", "방문 신청"
]

MENU_SIGNALS = [
    "주메뉴", "사하구 홈페이지", "만족도 조사", "개인정보처리방침",
    "저작권", "공유", "프린트", "이전글", "다음글", "목록"
]


# ==============================
# 유틸
# ==============================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def is_menu_like_chunk(text: str) -> bool:
    hit = sum(1 for x in MENU_SIGNALS if x in text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    short_lines = sum(1 for line in lines if len(line) <= 10)

    if hit >= 2:
        return True
    if lines and short_lines / len(lines) > 0.65:
        return True
    return False


# ==============================
# chunk 분리
# ==============================
def split_by_structure(text: str) -> List[str]:
    """
    문서를 먼저 구조 단위로 나눈다.
    - 제목/본문/구조정보
    - [표], [목록], [정의목록]
    - 신청방법, 구비서류 같은 섹션 제목
    """
    text = clean_text(text)
    if not text:
        return []

    # 구조 블록 기준 우선 분리
    blocks = re.split(r"\n(?=\[(?:본문|구조정보|표|목록|정의목록)\])", text)

    results = []
    for block in blocks:
        block = clean_text(block)
        if not block:
            continue

        # 섹션 힌트 앞에서 한 번 더 나눔
        section_pattern = r"\n(?=(?:%s)\s*[:：]?)" % "|".join(map(re.escape, SECTION_HINTS))
        sub_blocks = re.split(section_pattern, block)

        for sb in sub_blocks:
            sb = clean_text(sb)
            if sb:
                results.append(sb)

    return results


def sliding_window_split(text: str, max_len=MAX_CHUNK_LEN, overlap=OVERLAP) -> List[str]:
    """
    긴 텍스트는 문장 경계 비슷하게 나눈다.
    """
    text = clean_text(text)
    if len(text) <= max_len:
        return [text]

    chunks = []
    start = 0
    n = len(text)

    while start < n:
        end = min(start + max_len, n)
        piece = text[start:end]

        # 가능하면 줄바꿈이나 마침표 부근에서 끊기
        if end < n:
            cut_candidates = [
                piece.rfind("\n\n"),
                piece.rfind("\n"),
                piece.rfind(". "),
                piece.rfind("다. "),
            ]
            cut = max(cut_candidates)
            if cut > max_len // 2:
                end = start + cut + 1
                piece = text[start:end]

        piece = clean_text(piece)
        if piece:
            chunks.append(piece)

        if end >= n:
            break

        start = max(end - overlap, start + 1)

    return chunks


def build_chunk_text(doc, section_text: str) -> str:
    title = doc.get("title", "")
    menu_path = " > ".join(doc.get("menu_path", []))
    
    # [개선] section_text 내부에서 소제목(예: ## 구비서류)을 추출하여 맥락 보강
    # 정규표현식으로 첫 줄이 소제목인지 확인하는 로직 추가 가능
    
    prefix = f"### {title} ({menu_path}) ###"
    
    # 챗봇이 답변할 때 참고할 수 있도록 명확한 구분자 제공
    formatted_text = f"{prefix}\n\n[세부내용]\n{section_text}"
    
    return clean_text(formatted_text)

# prefix를 너무 많이 넣으면 결과가 다 비슷해짐, title, menu_path만 남기고 단순화
def make_chunks(doc: Dict) -> List[Dict]:
    text = clean_text(doc.get("text", ""))
    if not text:
        return []

    structured_blocks = split_by_structure(text)

    raw_chunks = []
    for block in structured_blocks:
        if len(block) <= MAX_CHUNK_LEN:
            raw_chunks.append(block)
        else:
            raw_chunks.extend(sliding_window_split(block))

    results = []
    chunk_index = 0

    for chunk in raw_chunks:
        chunk = clean_text(chunk)
        if len(chunk) < MIN_CHUNK_LEN:
            continue
        if is_menu_like_chunk(chunk):
            continue

        chunk_text = build_chunk_text(doc, chunk)

        results.append({
            "chunk_id": f"{doc.get('doc_id', 'unknown')}_{chunk_index}",
            "doc_id": doc.get("doc_id", ""),
            "url": doc.get("url", ""),
            "title": doc.get("title", ""),
            "author": doc.get("author", ""),
            "date": doc.get("date", ""),
            "views": doc.get("views"),
            "page_type": doc.get("page_type", ""),
            "parent_url": doc.get("parent_url", ""),
            "anchor_text": doc.get("anchor_text", ""),
            "menu_path": doc.get("menu_path", []),
            "chunk_index": chunk_index,
            "chunk_text": chunk_text,
            "source": doc.get("source", "saha.go.kr"),
        })
        chunk_index += 1

    return results


# ==============================
# 실행
# ==============================
def preprocess():
    ensure_dir(OUTPUT_DIR)

    total_docs = 0
    total_chunks = 0

    with open(INPUT_JSONL, "r", encoding="utf-8") as fin, \
         open(OUTPUT_JSONL, "w", encoding="utf-8") as fout:

        for line in fin:
            line = line.strip()
            if not line:
                continue

            doc = json.loads(line)
            total_docs += 1

            chunks = make_chunks(doc)
            total_chunks += len(chunks)

            for chunk in chunks:
                fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print("전처리 완료")
    print(f"- 입력 문서 수: {total_docs}")
    print(f"- 생성 chunk 수: {total_chunks}")
    print(f"- 출력 파일: {OUTPUT_JSONL}")


if __name__ == "__main__":
    preprocess()