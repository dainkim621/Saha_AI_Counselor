import os
import re
import json
from typing import List, Dict, Tuple

INPUT_FILE = "data/raw/saha_docs.jsonl"
OUTPUT_DIR = "data/processed"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "saha_chunks.jsonl")

MIN_CHUNK_LEN = 180
MAX_CHUNK_LEN = 650
OVERLAP_SENTENCES = 1

SECTION_HINTS = [
    "신청대상", "신청방법", "처리절차", "처리기간", "수수료",
    "구비서류", "제출서류", "유의사항", "문의처", "신고기한",
    "온라인 신청", "방문 신청", "지원대상", "지원내용",
    "이용방법", "이용시간", "접수처", "신청기한"
]

NOISE_LINE_PATTERNS = [
    r"^이전글.*",
    r"^다음글.*",
    r"^목록.*",
    r"^SNS.*공유.*",
    r"^공유.*",
    r"^프린트.*",
    r"^저작권.*",
    r"^개인정보처리방침.*",
    r"^만족도 조사.*",
    r"^페이지 만족도.*",
    r"^담당부서.*",
    r"^조회수.*",
    r"^등록일.*",
    r"^수정일.*",
    r"^첨부파일.*",
    r"^뷰어다운로드.*",
    r"^주메뉴.*",
    r"^통합검색.*",
    r"^홈페이지 의견수렴.*",
    r"^관련사이트.*",
    r"^콘텐츠 관리부서.*",
    r"^최종수정일.*",
]

BULLET_PATTERNS = [
    r"^[○●•▪■□▶▷☞※]\s*",
    r"^\d+\.\s*",
    r"^\d+\)\s*",
    r"^[가-힣A-Za-z]\.\s*",
    r"^-\s*",
]


def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


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


def remove_noise_lines(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        line = clean_inline_text(line)
        if not line:
            continue

        skip = False
        for pattern in NOISE_LINE_PATTERNS:
            if re.match(pattern, line):
                skip = True
                break

        if skip:
            continue

        if len(line) <= 1:
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def normalize_bullet(line: str) -> str:
    line = clean_inline_text(line)
    for pattern in BULLET_PATTERNS:
        line = re.sub(pattern, "", line)
    return clean_inline_text(line)


def is_section_header(line: str) -> bool:
    line = clean_inline_text(line)

    if not line:
        return False

    if line in SECTION_HINTS:
        return True

    if any(hint in line for hint in SECTION_HINTS) and len(line) <= 30:
        return True

    if line.endswith(":") and len(line) <= 30:
        return True

    return False


def split_korean_sentences(text: str) -> List[str]:
    """
    한국어 문장형 텍스트 분리
    - 종결 부호
    - 행정문서의 '...함', '...됨', '...다', '...요' 등도 어느 정도 반영
    """
    if not text:
        return []

    text = clean_inline_text(text)

    parts = re.split(r'(?<=[.!?])\s+|(?<=[다요죠음함됨])\s+', text)

    results = []
    for s in parts:
        s = clean_inline_text(s)
        if len(s) >= 8:
            results.append(s)

    return results


def split_long_sentence(sentence: str, max_len: int = MAX_CHUNK_LEN) -> List[str]:
    sentence = clean_inline_text(sentence)

    if len(sentence) <= max_len:
        return [sentence]

    parts = re.split(r'(?<=[,])\s+|(?<=[·:;])\s+|\s+', sentence)

    chunks = []
    current = ""

    for part in parts:
        part = clean_inline_text(part)
        if not part:
            continue

        candidate = f"{current} {part}".strip()
        if len(candidate) <= max_len:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = part

    if current:
        chunks.append(current)

    return chunks


def split_into_sections(text: str) -> List[Tuple[str, str]]:
    """
    줄바꿈 기반으로 섹션 분리
    반환: [(section_name, section_text), ...]
    """
    text = clean_text(text)
    blocks = re.split(r"\n{2,}", text)

    sections = []
    current_section = "일반"
    current_lines = []

    for block in blocks:
        block = clean_text(block)
        if not block:
            continue

        block_lines = [clean_inline_text(line) for line in block.split("\n") if clean_inline_text(line)]
        if not block_lines:
            continue

        first_line = block_lines[0]

        if is_section_header(first_line):
            if current_lines:
                sections.append((current_section, "\n".join(current_lines).strip()))
            current_section = normalize_bullet(first_line).rstrip(":")
            current_lines = block_lines[1:] if len(block_lines) > 1 else []
        else:
            current_lines.extend(block_lines)

    if current_lines:
        sections.append((current_section, "\n".join(current_lines).strip()))

    if not sections:
        sections.append(("일반", text))

    return sections


def section_text_to_units(section_text: str) -> List[str]:
    """
    섹션 텍스트를 chunk 빌드용 단위들로 변환
    - 항목형 줄은 항목별로 살리고
    - 문장형 문단은 문장 분리
    """
    units = []

    for raw_line in section_text.split("\n"):
        line = clean_inline_text(raw_line)
        if not line:
            continue

        normalized = normalize_bullet(line)

        # 짧은 항목형 라인 보존
        if raw_line.strip().startswith(("○", "●", "•", "▪", "■", "□", "▶", "▷", "☞", "※", "-")):
            if len(normalized) >= 6:
                units.append(normalized)
            continue

        if re.match(r"^\d+[\.\)]\s*", raw_line.strip()):
            if len(normalized) >= 6:
                units.append(normalized)
            continue

        # 일반 문장형 텍스트 분해
        sentences = split_korean_sentences(line)
        if sentences:
            units.extend(sentences)
        elif len(normalized) >= 6:
            units.append(normalized)

    return units


def build_chunks(units: List[str], min_len: int = MIN_CHUNK_LEN, max_len: int = MAX_CHUNK_LEN) -> List[str]:
    processed_units = []

    for unit in units:
        unit = clean_inline_text(unit)
        if not unit:
            continue

        if len(unit) > max_len:
            processed_units.extend(split_long_sentence(unit, max_len))
        else:
            processed_units.append(unit)

    chunks = []
    current_chunk = []

    for unit in processed_units:
        joined = " ".join(current_chunk + [unit]).strip()

        if len(joined) <= max_len:
            current_chunk.append(unit)
        else:
            if current_chunk:
                chunk_text = " ".join(current_chunk).strip()
                if len(chunk_text) >= min_len:
                    chunks.append(chunk_text)
                else:
                    if chunks:
                        chunks[-1] = f"{chunks[-1]} {chunk_text}".strip()
                    else:
                        chunks.append(chunk_text)

            if OVERLAP_SENTENCES > 0 and len(current_chunk) > 0:
                overlap = current_chunk[-OVERLAP_SENTENCES:]
                current_chunk = overlap + [unit]
            else:
                current_chunk = [unit]

    if current_chunk:
        chunk_text = " ".join(current_chunk).strip()
        if len(chunk_text) >= min_len:
            chunks.append(chunk_text)
        else:
            if chunks:
                chunks[-1] = f"{chunks[-1]} {chunk_text}".strip()
            else:
                chunks.append(chunk_text)

    # 최종 정리
    normalized_chunks = []
    for chunk in chunks:
        chunk = clean_inline_text(chunk)
        if len(chunk) >= 40:
            normalized_chunks.append(chunk)

    return normalized_chunks


def preprocess_document(doc: Dict, doc_index: int) -> List[Dict]:
    title = clean_inline_text(doc.get("title", ""))
    text = clean_text(doc.get("text", ""))
    url = doc.get("url", "")

    if not text or len(text) < 40:
        return []

    text = remove_noise_lines(text)

    if title and not text.startswith(title):
        text = f"{title}\n\n{text}"

    sections = split_into_sections(text)
    if not sections:
        return []

    chunks = []
    global_chunk_idx = 0

    for section_name, section_text in sections:
        section_name = clean_inline_text(section_name) or "일반"
        section_text = clean_text(section_text)

        if not section_text:
            continue

        units = section_text_to_units(section_text)
        if not units:
            continue

        chunk_texts = build_chunks(units)

        for local_idx, chunk_text in enumerate(chunk_texts):
            chunk_text = clean_inline_text(chunk_text)

            # 제목 + 섹션을 chunk 앞에 붙여 검색 강화
            prefix_parts = []
            if title:
                prefix_parts.append(f"[문서제목] {title}")
            if section_name and section_name != "일반":
                prefix_parts.append(f"[섹션] {section_name}")

            if prefix_parts:
                final_text = "\n".join(prefix_parts) + "\n" + chunk_text
            else:
                final_text = chunk_text

            chunk = {
                "chunk_id": f"doc{doc_index}_chunk{global_chunk_idx}",
                "doc_id": doc.get("doc_id", f"doc{doc_index}"),
                "title": title,
                "section": section_name,
                "url": url,
                "source": doc.get("source", "saha.go.kr"),
                "chunk_index": global_chunk_idx,
                "section_chunk_index": local_idx,
                "chunk_text": final_text,
                "length": len(final_text),
            }
            chunks.append(chunk)
            global_chunk_idx += 1

    return chunks


def run_preprocess():
    ensure_dir(OUTPUT_DIR)

    total_docs = 0
    total_chunks = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as infile, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as outfile:

        for doc_index, line in enumerate(infile):
            line = line.strip()
            if not line:
                continue

            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                print(f"[SKIP] JSON 파싱 실패 - line {doc_index + 1}")
                continue

            total_docs += 1
            chunks = preprocess_document(doc, doc_index)

            for chunk in chunks:
                outfile.write(json.dumps(chunk, ensure_ascii=False) + "\n")
                total_chunks += 1

    print("전처리 완료")
    print(f"- 문서 수: {total_docs}")
    print(f"- 생성된 chunk 수: {total_chunks}")
    print(f"- 저장 파일: {OUTPUT_FILE}")


if __name__ == "__main__":
    run_preprocess()