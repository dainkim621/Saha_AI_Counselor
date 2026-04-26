import os
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Notice

# openAI API 키
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def generate_embeddings():
    db: Session = SessionLocal()
    
    # 1. 임베딩이 아직 없는 데이터만 가져오기
    chunks = db.query(Notice).filter(Notice.embedding == None).all()
    print(f"🔄 총 {len(chunks)}개의 청크에 임베딩을 생성합니다...")

    for i, chunk in enumerate(chunks):
        try:
            # 2. OpenAI API를 이용해 임베딩 생성
            response = client.embeddings.create(
                input=chunk.chunk_text,
                model="text-embedding-3-small"
            )
            embedding_vector = response.data[0].embedding
            
            # 3. DB 업데이트
            chunk.embedding = embedding_vector
            
            if (i + 1) % 50 == 0:
                db.commit() # 50개마다 커밋
                print(f"✅ {i + 1}개 완료...")

        except Exception as e:
            print(f"🔥 에러 발생 ({chunk.chunk_id}): {e}")
            continue
            
    db.commit()
    print("✨ 모든 임베딩 저장이 완료되었습니다!")
    db.close()

if __name__ == "__main__":
    generate_embeddings()