# app/services/import_data.py
import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Notice

def import_jsonl_to_db(file_path: str):
    db: Session = SessionLocal()
    count = 0
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                
                # 중복 데이터 체크 (이미 들어있는 doc_id면 스킵)
                existing = db.query(Notice).filter(Notice.doc_id == data["doc_id"]).first()
                if existing:
                    continue
                
                # 데이터 매핑
                notice = Notice(
                    doc_id=data["doc_id"],
                    url=data["url"],
                    title=data["title"],
                    content=data["text"], # JSON의 text를 DB의 content로!
                    source=data.get("source", "saha.go.kr")
                )
                
                db.add(notice)
                count += 1
        
        db.commit()
        print(f"✅ 성공적으로 {count}개의 데이터를 DB에 넣었습니다!")
    except Exception as e:
        print(f"❌ 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # 파일 경로가 맞는지 확인하세요!
    import_jsonl_to_db("data/raw/saha_docs.jsonl")