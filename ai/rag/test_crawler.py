import json
import os

"""
file_path = "/data/raw/ooo.jsonl"

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
"""

#####
# passport_forms.jsonl 테스트하는거
#####

# 프로젝트 루트 기준 경로
file_path = "data/raw/passport_forms.jsonl"

# 파일 존재 여부 확인
if not os.path.exists(file_path):
    print(f"파일이 존재하지 않습니다: {file_path}")
    exit()

with open(file_path, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        line = line.strip()

        if not line:
            continue

        try:
            doc = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"[JSON 오류] line {i+1}: {e}")
            continue

        print("=" * 80)
        print(f"문서 번호: {i + 1}")

        print("제목:")
        print(doc.get("title", "제목 없음"))

        print("\nURL:")
        print(doc.get("url", "URL 없음"))

        print("\n카테고리:")
        print(doc.get("category", "카테고리 없음"))

        print("\n첨부파일:")
        attachments = doc.get("attachments", [])

        if attachments:
            for att in attachments:
                print(f" - 파일명: {att.get('file_name')}")
                print(f"   경로: {att.get('file_path')}")
        else:
            print("첨부파일 없음")

        print("\n본문 앞부분:")
        text_preview = doc.get("text", "")[:500]
        print(text_preview if text_preview else "본문 없음")

        print("\n문단 수:")
        print(len(doc.get("paragraphs", [])))

        print("\n원본 문서 키:")
        print(list(doc.keys()))

        # 5개만 출력
        if i >= 4:
            break