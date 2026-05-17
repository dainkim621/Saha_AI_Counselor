import json
import os
from dotenv import load_dotenv
from openai import OpenAI  # OpenAI 임베딩
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base  # app/database.py 확인
from app.models import Notice        # app/models/notice.py 확인

load_dotenv() # .env 파일의 내용을 환경변수로 불러옴
api_key = os.getenv("OPENAI_API_KEY")# os.getenv를 통해 안전하게 키를 가져옴
client = OpenAI(api_key=api_key)# 클라이언트를 생성할 때 변수를 넣어줌.

def get_embedding(text):
    """최신 클라이언트 방식으로 임베딩 생성"""
    # 텍스트를 벡터로 변환
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small" # 1536차원
    )
    return response.data[0].embedding
    
def import_chunks():
    print("🛠️ 테이블 확인 및 생성 중...")
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    file_path = "data/processed/saha_chunks.jsonl"
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    print("🚀 데이터 적재 및 임베딩 적재 시작...")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                
                # 중복 방지를 위해 chunk_id로 기존 데이터 확인
                existing_chunk = db.query(Notice).filter(Notice.chunk_id == data["chunk_id"]).first()
                
                if existing_chunk:
                    # 필요시 업데이트 로직
                    continue
                # 임베딩 생성 (최신 client 사용)
                print(f"임베딩 생성 중: {data['title']}")
                vector_data = get_embedding(data["chunk_text"])
                
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
                    chunk_index=data["chunk_index"],
                    embedding=vector_data # 생성된 벡터 데이터 삽입
                )
                db.add(new_chunk)
            
            db.commit()
            print("✅ 모든 데이터와 벡터가 성공적으로 적재되었습니다!")
            
    except Exception as e:
        print(f"🔥 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_chunks()