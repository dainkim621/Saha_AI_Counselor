import json
import os
from dotenv import load_dotenv
from openai import OpenAI  
from sqlalchemy.orm import Session
from app.database import SessionLocal, engine, Base  
from app.models import Notice        
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter

load_dotenv() 
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=100
)

def get_embedding(text):
    """OpenAI 1536차원 임베딩 생성"""
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small" 
    )
    return response.data[0].embedding


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
            if not raw_published_at or str(raw_published_at).strip() == "":
                raw_published_at = None
            
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
    print("🚀 JSONL 데이터 통합 적재 시작")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(
        os.path.join(current_dir, "..", "..")
    )

    processed_dir = os.path.join(project_root, "data", "processed")

    # 적재할 JSONL 파일 3개
    file_names = [
        "saha_clean_chunks.jsonl",
        "health_chunks_once.jsonl",
        "staff_chunks_once.jsonl",
    ]

    # 기존 테이블을 삭제하지 않고, 없는 테이블만 생성
    # Notice 테이블만 삭제
    Notice.__table__.drop(bind=engine, checkfirst=True)

    # Notice 테이블 다시 생성
    Notice.__table__.create(bind=engine, checkfirst=True)

    print("✅ Notice 테이블 초기화 완료!")
    db: Session = SessionLocal()

    total_inserted = 0
    total_skipped = 0

    try:
        for file_name in file_names:
            file_path = os.path.join(processed_dir, file_name)

            if not os.path.exists(file_path):
                print(f"❌ 파일 없음: {file_path}")
                continue

            print(f"\n📂 적재 시작: {file_name}")

            inserted = 0
            skipped = 0

            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()

                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                    except json.JSONDecodeError:
                        print("⚠️ JSON 파싱 실패: 건너뜀")
                        skipped += 1
                        continue

                    chunk_id = data.get("chunk_id")
                    content_text = data.get("chunk_text", "").strip()

                    if not chunk_id or not content_text:
                        skipped += 1
                        continue

                    # 이미 적재된 청크는 건너뛰기
                    existing = (
                        db.query(Notice)
                        .filter(Notice.chunk_id == chunk_id)
                        .first()
                    )

                    if existing:
                        skipped += 1
                        continue

                    print(
                        f"🔮 임베딩 생성: "
                        f"{data.get('title', '정보')} ({chunk_id})"
                    )

                    # OpenAI 임베딩 생성
                    vector_data = get_embedding(content_text)

                    new_chunk = Notice(
                        chunk_id=chunk_id,
                        doc_id=data.get("doc_id"),
                        url=data.get("url"),
                        title=data.get("title", "정보 없음"),
                        page_type=data.get("page_type", "contents"),
                        source=data.get("source", "saha.go.kr"),
                        menu_path=data.get("menu_path", []),
                        published_at=data.get("published_at") or None,
                        chunk_text=content_text,
                        chunk_index=data.get("chunk_index", 0),
                        embedding=vector_data,
                        text_hash=data.get("text_hash"),
                        major=data.get("major", ""),
                        minor=data.get("minor", ""),
                        context=data.get("context", "")
                    )

                    db.add(new_chunk)
                    inserted += 1

                    # 10개마다 저장
                    if inserted % 10 == 0:
                        db.commit()
                        print(f"💾 {file_name}: {inserted}개 저장")

            # 해당 파일의 남은 데이터 저장
            db.commit()

            total_inserted += inserted
            total_skipped += skipped

            print(
                f"✅ {file_name} 완료 "
                f"(추가: {inserted}개, 건너뜀: {skipped}개)"
            )

        print("\n🎉 전체 적재 완료!")
        print(f"신규 적재: {total_inserted}개")
        print(f"건너뛴 청크: {total_skipped}개")

    except Exception as e:
        db.rollback()
        print(f"❌ 적재 중 오류 발생: {type(e).__name__}: {e}")
        raise

    finally:
        db.close()

if __name__ == "__main__":
    import_chunks()