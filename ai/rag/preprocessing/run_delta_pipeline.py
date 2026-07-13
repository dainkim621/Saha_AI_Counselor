import os
import json
import psycopg2
from ai.rag.preprocessing.preprocess_exe import run_preprocessing_pipeline
from app.services.import_data import delete_chunks_by_doc_id, insert_delta_chunks
from app.database import SessionLocal, engine, Base

DATA_DIR = "data"
OUTPUT_LATEST_JSONL = os.path.join(DATA_DIR, "processed", "delta", "saha_clean_delta.jsonl") # 전처리 파일
#OUTPUT_HTML = os.path.join(DATA_DIR, "delta", "delta_review_dashboard.html") # 전처리 검수용 파일

def get_db_connection():
    return psycopg2.connect(host="localhost", database="saha_chatbot_db", user="saha_user", password="saha_password123!")

def main():
    print("🌙 델타 동기화 및 단일 파일 추출 가동...")
    
    db = SessionLocal()
    
    # 변경분 파일 경로
    delta_file_paths = {
        "general": os.path.join(DATA_DIR, "raw", "delta", "saha_docs_delta.jsonl"),
        "civil": os.path.join(DATA_DIR, "raw", "delta", "saha_civil_forms_delta.jsonl"),
        "bid": os.path.join(DATA_DIR, "raw", "delta", "saha_bid_docs_delta.jsonl"),
        "waste": os.path.join(DATA_DIR, "raw", "delta", "saha_waste_docs_delta.jsonl")
    }
    
    # 전체 크롤링 데이터 파일 경로 
    raw_file_paths = {
        "general": os.path.join(DATA_DIR, "raw", "saha_docs.jsonl"),
        "civil": os.path.join(DATA_DIR, "raw", "saha_civil_forms.jsonl"),
        "bid": os.path.join(DATA_DIR, "raw", "saha_bid_docs.jsonl"),
        "waste": os.path.join(DATA_DIR, "raw", "saha_waste_docs.jsonl")
    }
    
    try:
        # [1단계] 수정된 문서 ID 수집 및 기존 DB 데이터 삭제
        updated_doc_ids = set()
        target_doc_ids = set()
        
        for cat, path in delta_file_paths.items():
            if not os.path.exists(path): continue
            
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip(): continue
                    log_data = json.loads(line.strip())
                    
                    doc_id = log_data.get("doc_id") 
                    change_type = log_data.get("change_type")
                    
                    if not doc_id: continue
                    target_doc_ids.add(doc_id)
                    
                    # 수정된 문서는 DB에서 청크 날리기
                    # [최종 버전의 올바른 모습]
                    if change_type == "UPDATED_DOCUMENT" and doc_id not in updated_doc_ids:
                        delete_chunks_by_doc_id(db, doc_id) # cursor와 cat 대신 db(세션)만 넘김!
                        updated_doc_ids.add(doc_id)
        
        if not target_doc_ids:
            print("💤 오늘 추가/변경된 문서가 없어 파이프라인을 종료합니다.")
            return

        # [2단계] 전체 데이터를 전처리 함수에 넣고, 오늘 타겟인 청크들만 쏙쏙 뽑아내기
        print("▶ 원본 파일에서 새 청크 추출 중...")
        all_raw_chunks = run_preprocessing_pipeline(raw_file_paths)
        
        # 오늘 DB에 들어갈 알짜배기 청크들만 담을 단일 리스트
        final_delta_chunks = [chunk for chunk in all_raw_chunks if chunk.get("doc_id") in target_doc_ids]
        
        # [3단계] 추출된 청크들을 단 하나의 JSONL 파일로 덮어쓰기 저장 (영수증 생성)
        os.makedirs(os.path.dirname(OUTPUT_LATEST_JSONL), exist_ok=True)
        with open(OUTPUT_LATEST_JSONL, "w", encoding="utf-8") as out_f:
            for chunk in final_delta_chunks:
                out_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
        print(f"📄 [파일 저장 완료] 오늘 갱신된 {len(final_delta_chunks)}개 청크가 {OUTPUT_LATEST_JSONL} 에 저장되었습니다.")

        # [4단계] 안전하게 모인 청크들을 DB에 Insert!
        print("▶ 임베딩 생성 및 DB 적재 시작...")
        # ✅ 우리가 새로 만든 SQLAlchemy용 적재 함수 사용! (for문도 함수 안에 이미 다 들어있어요)
        insert_delta_chunks(db, final_delta_chunks) 
                
        db.commit() # ✅ db 세션으로 커밋!
        print("✅ [파이프라인 종료] 델타 데이터 DB 갱신이 완벽하게 끝났습니다!")
        
    except Exception as e:
        db.rollback() # ✅ db 세션으로 롤백!
        print(f"❌ 파이프라인 가동 중 에러 발생 (롤백됨): {e}")
    finally:
        db.close() # ✅ db 세션 닫기! (cursor 닫을 필요 없음)

if __name__ == "__main__":
    main()