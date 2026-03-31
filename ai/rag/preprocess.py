import os
import re
import json
from typing import List, Dict

INPUT_FILE = "data/raw/saha_docs.jsonl"
OUTPUT_DIR = "data/processed"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "saha_chunks.jsonl")

MIN_CHUNK_LEN = 150     # 너무 짧은 chunk 방지
MAX_CHUNK_LEN = 700     # AI가 읽기 좋은 적당한 길이
OVERLAP_SENTENCES = 1   # 문맥 유지를 위한 문장 중복

def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_korean_sentences(text: str) -> List[str]:
    """
    한국어 문장 기준으로 대략 분리
    종결 표현 + ., ?, ! 기준
    """
    if not text:
        return []

    text = clean_text(text)

    # 문장 끝 후보 뒤에서 자르기
    sentences = re.split(r'(?<=[.!?])\s+|(?<=[다요죠음함됨])\s+', text)

    results = []
    for s in sentences:
        s = clean_text(s)
        if len(s) >= 10:
            results.append(s)

    return results


def split_long_sentence(sentence: str, max_len: int = MAX_CHUNK_LEN) -> List[str]:
    """
    한 문장이 너무 길면 쉼표/공백 기준으로 분할
    """
    sentence = clean_text(sentence)

    if len(sentence) <= max_len:
        return [sentence]

    parts = re.split(r'(?<=[,])\s+|(?<=[·])\s+|\s+', sentence)

    chunks = []
    current = ""

    for part in parts:
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


def build_chunks(sentences: List[str], min_len: int = MIN_CHUNK_LEN, max_len: int = MAX_CHUNK_LEN) -> List[str]:
    """
    문장 단위로 chunk 생성
    - 너무 짧으면 다음 문장과 합침
    - 너무 길면 분리
    - overlap으로 문맥 유지
    """
    processed_sentences = []

    for sent in sentences:
        if len(sent) > max_len:
            processed_sentences.extend(split_long_sentence(sent, max_len))
        else:
            processed_sentences.append(sent)

    chunks = []
    current_chunk = []

    for sent in processed_sentences:
        joined = " ".join(current_chunk + [sent]).strip()

        if len(joined) <= max_len:
            current_chunk.append(sent)
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

            # overlap 적용
            if OVERLAP_SENTENCES > 0 and len(current_chunk) > 0:
                overlap = current_chunk[-OVERLAP_SENTENCES:]
                current_chunk = overlap + [sent]
            else:
                current_chunk = [sent]

    if current_chunk:
        chunk_text = " ".join(current_chunk).strip()
        if len(chunk_text) >= min_len:
            chunks.append(chunk_text)
        else:
            if chunks:
                chunks[-1] = f"{chunks[-1]} {chunk_text}".strip()
            else:
                chunks.append(chunk_text)

    return chunks


def preprocess_document(doc: Dict, doc_index: int) -> List[Dict]:
    title = clean_text(doc.get("title", ""))
    text = clean_text(doc.get("text", ""))
    url = doc.get("url", "")

    if not text or len(text) < 30:
        return []

    # 제목을 앞에 붙여주면 검색 품질이 좋아짐
    full_text = f"{title}\n{text}" if title else text

    sentences = split_korean_sentences(full_text)
    if not sentences:
        return []

    chunk_texts = build_chunks(sentences)

    chunks = []
    for idx, chunk_text in enumerate(chunk_texts):
        chunk = {
            "chunk_id": f"doc{doc_index}_chunk{idx}",
            "doc_id": doc.get("doc_id", f"doc{doc_index}"),
            "title": title,
            "url": url,
            "source": doc.get("source", "saha.go.kr"),
            "chunk_index": idx,
            "chunk_text": chunk_text,
            "length": len(chunk_text),
        }
        chunks.append(chunk)

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

    print(f"전처리 완료")
    print(f"- 문서 수: {total_docs}")
    print(f"- 생성된 chunk 수: {total_chunks}")
    print(f"- 저장 파일: {OUTPUT_FILE}")


if __name__ == "__main__":
    run_preprocess()