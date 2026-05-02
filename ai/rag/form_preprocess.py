import os
import json
import re

INPUT_FILE = "data/raw/saha_civil_forms.jsonl"
OUTPUT_FILE = "data/processed/form_chunks.jsonl"

MIN_LEN = 30
MAX_LEN = 500


def clean_text(text):
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def split_text(text):
    sentences = re.split(r"(?<=[.!?다])\s+", text)

    chunks = []
    current = ""

    for s in sentences:
        s = clean_text(s)

        if not s:
            continue

        candidate = (current + " " + s).strip()

        if len(candidate) <= MAX_LEN:
            current = candidate
        else:
            if len(current) >= MIN_LEN:
                chunks.append(current)
            current = s

    if len(current) >= MIN_LEN:
        chunks.append(current)

    return chunks


def build_text(doc):
    parts = []

    if doc.get("title"):
        parts.append(f"제목: {doc['title']}")

    fields = [
        "required_documents",
        "submission_place",
        "processing_period",
        "fee",
        "notes",
        "workflow"
    ]

    for f in fields:
        val = doc.get(f)
        if val:
            parts.append(f"{f}: {val}")

    return "\n".join(parts)


def preprocess():
    os.makedirs("data/processed", exist_ok=True)

    total_docs = 0
    total_chunks = 0

    with open(INPUT_FILE, "r", encoding="utf-8") as f, \
         open(OUTPUT_FILE, "w", encoding="utf-8") as out:

        for line in f:
            doc = json.loads(line)

            text = build_text(doc)
            text = clean_text(text)

            if len(text) < 50:
                continue

            chunks = split_text(text)

            for i, chunk in enumerate(chunks):
                data = {
                    "chunk_id": f"{doc['doc_id']}_chunk{i}",
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "category": doc.get("category"),
                    "chunk_index": i,
                    "chunk_text": chunk,
                    "length": len(chunk),
                    "source_url": doc["url"],
                    "data_type": "civil_form"
                }

                out.write(json.dumps(data, ensure_ascii=False) + "\n")
                total_chunks += 1

            total_docs += 1

    print("전처리 완료")
    print(f"문서 수: {total_docs}")
    print(f"청크 수: {total_chunks}")
    print(f"파일: {OUTPUT_FILE}")


if __name__ == "__main__":
    preprocess()