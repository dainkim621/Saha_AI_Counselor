import os
import json
import psycopg2
from ai.rag.preprocessing.preprocess_exe import run_preprocessing_pipeline
from app.services.import_data import delete_chunks_by_doc_id, insert_delta_chunks
from app.database import SessionLocal, engine, Base
from app.models import Notice
DATA_DIR = "data"
OUTPUT_LATEST_JSONL = os.path.join(DATA_DIR, "processed", "delta", "saha_clean_delta.jsonl") # 전처리 파일
#OUTPUT_HTML = os.path.join(DATA_DIR, "delta", "delta_review_dashboard.html") # 전처리 검수용 파일

def get_db_connection():
    return psycopg2.connect(host="localhost", database="saha_chatbot_db", user="saha_user", password="saha_password123!")


def main():
    print("🌙 델타 동기화 시작...")

    delta_file_paths = {
        "general": os.path.join(DATA_DIR, "raw", "delta", "saha_docs_delta.jsonl"),
        "civil": os.path.join(DATA_DIR, "raw", "delta", "saha_civil_forms_delta.jsonl"),
        "bid": os.path.join(DATA_DIR, "raw", "delta", "saha_bid_docs_delta.jsonl"),
        "waste": os.path.join(DATA_DIR, "raw", "delta", "saha_waste_docs_delta.jsonl"),
    }

    raw_file_paths = {
        "general": os.path.join(DATA_DIR, "raw", "saha_docs.jsonl"),
        "civil": os.path.join(DATA_DIR, "raw", "saha_civil_forms.jsonl"),
        "bid": os.path.join(DATA_DIR, "raw", "saha_bid_docs.jsonl"),
        "waste": os.path.join(DATA_DIR, "raw", "saha_waste_docs.jsonl"),
    }

    # 1. 신규 및 변경 문서 ID 수집
    target_doc_ids = set()

    for path in delta_file_paths.values():
        if not os.path.exists(path):
            continue

        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue

                doc = json.loads(line)
                doc_id = doc.get("doc_id")

                if doc_id and doc.get("change_type") in (
                    "NEW_DOCUMENT", "UPDATED_DOCUMENT"
                ):
                    target_doc_ids.add(doc_id)

    if not target_doc_ids:
        print("💤 처리할 신규·변경 문서가 없습니다.")
        return

    print(f"📄 처리 대상 문서: {len(target_doc_ids)}개")

    # 2. DB를 수정하기 전에 전체 원본 데이터 전처리
    all_chunks = run_preprocessing_pipeline(raw_file_paths)

    # 전처리 결과가 비정상적으로 비어 있으면 기존 파일 보호
    if not all_chunks:
        print("❌ 전체 전처리 결과가 비어 있어 동기화를 중단합니다.")
        return

    # 전체 전처리 결과를 통합 JSONL 파일에 저장
    # 임시 파일을 먼저 생성한 뒤 교체하여 파일 손상 방지
    full_output_path = os.path.join(
        DATA_DIR, "processed", "saha_clean_chunks.jsonl"
    )
    temp_output_path = full_output_path + ".tmp"

    os.makedirs(os.path.dirname(full_output_path), exist_ok=True)

    with open(temp_output_path, "w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    os.replace(temp_output_path, full_output_path)

    print(f"✅ 통합 전처리 파일 갱신 완료: {len(all_chunks)}개 청크")

    final_delta_chunks = [
        chunk for chunk in all_chunks
        if chunk.get("doc_id") in target_doc_ids
        and (chunk.get("chunk_text") or "").strip()
    ]

    chunks_by_doc = {}
    for chunk in final_delta_chunks:
        chunks_by_doc.setdefault(chunk["doc_id"], []).append(chunk)

    missing_ids = target_doc_ids - set(chunks_by_doc)

    if missing_ids:
        print(f"⚠️ 전처리 결과가 없는 문서: {len(missing_ids)}개")
        print("⏩ 해당 문서는 건너뛰고 정상 문서만 DB에 반영합니다.")
        print("🔒 건너뛴 문서의 기존 DB 데이터는 유지됩니다.")

        # 추후 원인 분석을 위해 처리하지 못한 문서 ID 기록
        skipped_path = os.path.join(
            DATA_DIR, "processed", "delta", "skipped_doc_ids.jsonl"
        )
        os.makedirs(os.path.dirname(skipped_path), exist_ok=True)

        with open(skipped_path, "w", encoding="utf-8") as f:
            for doc_id in sorted(missing_ids):
                f.write(json.dumps({
                    "doc_id": doc_id,
                    "reason": "전처리 결과 없음"
                }, ensure_ascii=False) + "\n")

    # 3. DB의 기존 데이터와 비교하여 필요한 문서만 갱신
    db = SessionLocal()

    try:
        chunks_to_insert = []
        changed_count = 0
        unchanged_count = 0

        for doc_id, new_chunks in chunks_by_doc.items():
            existing_chunks = (
                db.query(Notice)
                .filter(Notice.doc_id == doc_id)
                .all()
            )

            existing_hashes = sorted(
                (c.chunk_index, c.text_hash)
                for c in existing_chunks
            )

            new_hashes = sorted(
                (c["chunk_index"], c["text_hash"])
                for c in new_chunks
            )

            if existing_chunks and existing_hashes == new_hashes:
                unchanged_count += 1
                continue

            if existing_chunks:
                delete_chunks_by_doc_id(db, doc_id)

            chunks_to_insert.extend(new_chunks)
            changed_count += 1

        # 4. 임베딩 생성 및 DB 적재
        if chunks_to_insert:
            print(f"🔮 적재할 청크: {len(chunks_to_insert)}개")
            insert_delta_chunks(db, chunks_to_insert)

        db.commit()

        # 5. 정상 반영된 변경분 기록
        os.makedirs(os.path.dirname(OUTPUT_LATEST_JSONL), exist_ok=True)

        with open(OUTPUT_LATEST_JSONL, "w", encoding="utf-8") as out_f:
            for chunk in chunks_to_insert:
                out_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")

        print(f"✅ 갱신 문서: {changed_count}개")
        print(f"⏩ 변경 없는 문서: {unchanged_count}개")
        print("✅ 델타 동기화 완료!")

    except Exception as e:
        db.rollback()
        print(f"❌ 델타 동기화 실패: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    main()
