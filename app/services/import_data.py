import json
import os
from dotenv import load_dotenv
from openai import OpenAI  
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base  
from app.models import Notice        

load_dotenv() 
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def get_embedding(text):
    """최신 클라이언트 방식으로 OpenAI 1536차원 임베딩 생성"""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small" 
    )
    return response.data[0].embedding
    
def import_chunks():
    print("🛠️ 테이블 확인 및 생성 중...")
    # ⚠️ 스키마가 대폭 변경되었으므로, 안전한 반영을 위해 기존 테이블을 한 번 밀고 생성하는 것을 추천합니다.
    Base.metadata.drop_all(bind=engine) 
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    file_path = "data/processed/saha_chunks.jsonl"
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    print("🚀 데이터 적재 및 OpenAI 벡터 변환 시작...")
    
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                data = json.loads(line)
                
                # 중복 적재 방지 (chunk_id 기준)
                existing_chunk = db.query(Notice).filter(Notice.chunk_id == data["chunk_id"]).first()
                if existing_chunk:
                    continue
                
                print(f"임베딩 생성 중 ➡️ {data['title']} ({data['chunk_id']})")
                vector_data = get_embedding(data["chunk_text"])
                
                # 내부 메타데이터 딕셔너리 안전하게 추출
                meta = data.get("metadata", {})
                
                # 분기 처리에 따라 누락될 수 있는 컬럼들은 .get()으로 방어적 처리
                new_chunk = Notice(
                    chunk_id=data["chunk_id"],
                    doc_id=data["doc_id"],
                    url=data["url"],
                    title=data["title"],
                    source=data.get("source", "saha.go.kr"),
                    menu_path=data.get("menu_path", []), # JSON 컬럼에 리스트 그대로 주입
                    chunk_text=data["chunk_text"],
                    
                    
                    # 서식 B에는 존재하고 서식 A에는 없을 수 있는 기존 필드들 방어 처리
                    author=meta.get("author", "미확인"),
                    published_at=meta.get("date", ""), 
                    views=int(data.get("views", 0) or 0),
                    chunk_index=data.get("chunk_index", 0),
                    #full_text=data.get("full_text", None)
                    
                    # 💡 새로 설계한 지능형 전처리 구조화 필드 매핑
                    major=meta.get("major", ""),
                    minor=meta.get("minor", ""),
                    context=meta.get("context", ""),
                    
                    # pgvector 컬럼에 1536차원 실수 리스트 적재
                    embedding=vector_data 
                )
                db.add(new_chunk)
            
            db.commit()
            print("✅ [성공] 모든 뒤죽박죽 데이터가 완벽한 위계 구조와 함께 벡터 DB에 적재되었습니다!")
            
    except Exception as e:
        print(f"🔥 적재 중 크리티컬 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    import_chunks()