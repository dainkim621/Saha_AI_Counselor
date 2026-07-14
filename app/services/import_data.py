import json
import os
from dotenv import load_dotenv
from openai import OpenAI  
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base  
from app.models import Notice        
from datetime import datetime

load_dotenv() 
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

def get_embedding(text):
    """OpenAI 1536차원 임베딩 생성"""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small" 
    )
    return response.data[0].embedding

# app/import_data.py (기존 파일에 추가)

# app/import_data.py (기존 수빈님 코드 아래에 이어서 추가)

def delete_chunks_by_doc_id(db: Session, doc_id: str):
    """
    [새벽 델타용] 업데이트(update)된 문서의 기존 청크 데이터를 싹 비워주는 함수
    """
    try:
        # Notices 테이블에서 doc_id가 일치하는 행들을 모두 찾아 삭제합니다.
        deleted_count = db.query(Notice).filter(Notice.doc_id == doc_id).delete()
        print(f"   🗑️ [DB 삭제 성공] doc_id: {doc_id} (총 {deleted_count}개 청크 비움)")
    except Exception as e:
        print(f"   ❌ [DB 삭제 실패] doc_id: {doc_id}, 에러: {e}")
        raise e

def insert_delta_chunks(db: Session, chunks_list: list):
    """
    [새벽 델타용] 전처리가 끝난 청크 리스트를 받아 OpenAI 임베딩을 먹이고 DB에 저장하는 함수
    """
    count = 0
    try:
        for data in chunks_list:
            chunk_id = data.get("chunk_id")
            content_text = data.get("chunk_text", "").strip()
            
            if not chunk_id or not content_text:
                continue
                
            # 중복 적재 방지
            existing_chunk = db.query(Notice).filter(Notice.chunk_id == chunk_id).first()
            if existing_chunk:
                continue
            
            raw_published_at = data.get("published_at")
            if not raw_published_at or raw_published_at.strip() == "":
                raw_published_at = None # 빈 문자열 대신 NULL(None)을 넣음
            
            print(f"🔮 임베딩 생성 중 ➡️ {data.get('title', '정보')} ({chunk_id})")
            
            # 수빈님이 짠 OpenAI 임베딩 함수 호출
            vector_data = get_embedding(content_text) 
            
            new_chunk = Notice(
                chunk_id=chunk_id,  
                doc_id=data.get("doc_id"),
                url=data.get("url"),
                title=data.get("title", "정보 없음"),
                page_type=data.get("page_type", "contents"),
                source=data.get("source", "saha.go.kr"),
                menu_path=data.get("menu_path", []),
                chunk_text=content_text,
                text_hash=data.get("text_hash"),
                chunk_index=data.get("chunk_index", 0),
                embedding=vector_data, # 생성된 벡터값 쏙 넣기
                major=data.get("major", ""),
                minor=data.get("minor", ""),
                context=data.get("context", "")
            )
            db.add(new_chunk)
            count += 1
            
        print(f"💾 {count}개의 새로운 델타 데이터 DB 적재 준비 완료.")
        
    except Exception as e:
        print(f"🔥 델타 적재 중 에러 발생: {e}")
        raise e
    
def import_chunks():
    print("🛠️ 테이블 확인 및 생성 중...")
    # 기존 테이블을 삭제 후 새로 생성
    Base.metadata.drop_all(bind=engine) 
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    current_dir = os.path.dirname(os.path.abspath(__file__)) # app/services
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..")) # 최상위 루트
    file_path = os.path.join(project_root, "data", "processed", "saha_clean_chunks.jsonl")
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    print("🚀 데이터 적재 및 OpenAI 벡터 변환 시작...")
    
    count = 0
    try:
        # 한 줄씩 읽으면서 바로 파싱
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    print(f"⚠️ 줄 파싱 실패 (스킵): {line[:30]}...")
                    continue
                
                # 전처리 완료된 필수 식별자 컬럼 체크
                chunk_id = data.get("chunk_id")
                if not chunk_id:
                    continue
                    
                # 중복 적재 방지(chunk_id로 조회)
                existing_chunk = db.query(Notice).filter(Notice.chunk_id == chunk_id).first()
                if existing_chunk:
                    continue
                
                # 최종 정제 파일의 본문 키값은 'chunk_text'
                content_text = data.get("chunk_text", "").strip()
                if not content_text:
                    continue
                
                print(f"🔮 임베딩 생성 중 ➡️ {data.get('title', '정보')} ({chunk_id})")
                
                # OpenAI 임베딩 생성
                vector_data = get_embedding(content_text)
                
                # DB 데이터 모델 생성 
                new_chunk = Notice(
                    chunk_id=chunk_id,  
                    doc_id=data.get("doc_id"),
                    url=data.get("url"),
                    title=data.get("title", "정보 없음"),
                    page_type=data.get("page_type", "contents"),
                    source=data.get("source", "saha.go.kr"),
                    menu_path=data.get("menu_path", []),
                    published_at=data.get("published_at", None),
                    chunk_text=content_text,
                    chunk_index=data.get("chunk_index", 0),
                    embedding=vector_data,
                    text_hash=data.get("text_hash"),
                    # 수집 데이터 최상위에 평탄화되어 있는 필드들을 안전하게 백업
                    major=data.get("major", ""),
                    minor=data.get("minor", ""),
                    context=data.get("context", "")
                )
                db.add(new_chunk)
                count += 1
                
                # 10개 단위로 트랜잭션 중간 커밋
                if count % 10 == 0:
                    db.commit()
                    print(f"💾 중간 저장 완료 ({count}개 완료...)")
        
        # 남은 조각 최종 커밋
        db.commit()
        print(f"\n✅ [성공] 총 {count}개의 데이터가 벡터 DB에 적재되었습니다!")
        
    except Exception as e:
        print(f"🔥 적재 중 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()
        
if __name__ == "__main__":
    import_chunks()