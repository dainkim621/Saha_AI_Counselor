import json

file_path = "data/processed/saha_chunks.jsonl"

with open(file_path, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        chunk = json.loads(line)
        print("=" * 80)
        print("chunk_id:", chunk["chunk_id"])
        print("title:", chunk["title"])
        print("url:", chunk["url"])
        print("length:", chunk["length"])
        print("chunk_text:", chunk["chunk_text"])

        if i >= 4:
            break