import json

file_path = "data/raw/saha_docs.jsonl"

with open(file_path, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        doc = json.loads(line)
        print("=" * 80)
        print("문서 번호:", i + 1)
        print("제목:", doc.get("title"))
        print("URL:", doc.get("url"))
        print("본문 앞부분:", doc.get("text", "")[:300])
        print("문단 수:", len(doc.get("paragraphs", [])))

        if i >= 4:   # 5개만 보기
            break