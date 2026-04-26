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
                # 1. 여기서 변수명을 'data'로 설정함
                data = json.loads(line)
                
                # 중복 데이터 체크
                existing = db.query(Notice).filter(Notice.doc_id == data["doc_id"]).first()
                if existing:
                    continue
                
                # 2. 아래 Notice 객체 생성 시 모든 변수명을 'data'로 통일!
                notice = Notice(
                    doc_id=data.get("doc_id"),
                    url=data.get("url"),
                    title=data.get("title"),
                    author=data.get("author", ""),
                    published_at=data.get("date", ""), # 친구의 date 필드를 published_at에 매칭
                    views=int(data.get("views")) if data.get("views") else 0,
                    text=data.get("text", ""),
                    paragraphs=data.get("paragraphs", []),
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
    # 데이터 파일 경로가 정확한지 다시 한 번 확인!
    import_jsonl_to_db("data/raw/saha_docs.jsonl")