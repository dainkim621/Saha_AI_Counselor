import json
import os
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base  # app/database.py 확인
from app.models import Notice        # app/models/notice.py 확인

def load_data():
    # 테이블이 혹시 안 만들어졌을까봐 안전하게 한 번 더 생성 명령 (선택사항)
    # Base.metadata.create_all(bind=engine) 

    db: Session = SessionLocal()
    # 경로가 root 기준인지 확인 (Saha_AI_Counselor 폴더에서 실행하니까 맞을 거예요)
    file_path = "data/processed/saha_chunks.jsonl"
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    print("🚀 청크 데이터 적재 시작...")
    
def import_chunks():
    print("🛠️ 테이블 확인 및 생성 중...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    file_path = "data/processed/saha_chunks.jsonl"
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    print("🚀 데이터 적재를 시작합니다...")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                
                # 중복 방지를 위해 chunk_id로 기존 데이터 확인
                existing_chunk = db.query(Notice).filter(Notice.chunk_id == data["chunk_id"]).first()
                
                if existing_chunk:
                    # 필요시 업데이트 로직
                    continue
                
                new_chunk = Notice(
                    chunk_id=data["chunk_id"],
                    doc_id=data["doc_id"],
                    url=data["url"],
                    title=data["title"],
                    author=data.get("author", "미확인"),
                    published_at=data["date"],
                    views=int(data.get("views", 0) or 0),
                    menu_path=data["menu_path"],
                    chunk_text=data["chunk_text"],
                    chunk_index=data["chunk_index"]
                )
                db.add(new_chunk)
            
            db.commit()
            print("✅ 모든 청크가 성공적으로 적재되었습니다!")
            
    except Exception as e:
        print(f"🔥 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_chunks()