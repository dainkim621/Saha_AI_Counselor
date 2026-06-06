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
    # 스키마 갱신을 위해 기존 테이블을 싹 밀고 새로 생성
    Base.metadata.drop_all(bind=engine) 
    Base.metadata.create_all(bind=engine)
    
    db: Session = SessionLocal()
    current_dir = os.path.dirname(os.path.abspath(__file__)) # app/services
    project_root = os.path.abspath(os.path.join(current_dir, "..", "..")) # 최상위 루트
    file_path = os.path.join(project_root, "data", "processed", "saha_clean_docs.jsonl")
    
    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    print("🚀 데이터 적재 및 OpenAI 벡터 변환 시작...")
    
    count = 0
    try:
        # 💡 [정석 해결책] 파일 전체를 텍스트로 통째로 읽어옵니다.
        with open(file_path, "r", encoding="utf-8") as f:
            raw_text = f.read().strip()
            
        # 전처리 스크립트 특성상 맨 마지막 콤마(Category 노이즈 등)가 꼬였을 때를 대비해 양끝 정리
        if raw_text.endswith(","):
            raw_text = raw_text[:-1].strip()
        if not raw_text.endswith("]"):
            raw_text += "]"
            
        # 통짜 JSON 리스트로 변환
        try:
            data_list = json.loads(raw_text)
        except json.JSONDecodeError as je:
            print(f"⚠️ 통짜 파싱 실패로 강제 정규식 추출 모드 전환: {je}")
            # 만약 대괄호 매칭이 깨졌다면 내부 중괄호 객체들만 강제로 뜯어내기
            import re
            records = re.findall(r'\{[^{}]+\}', raw_text)
            data_list = []
            for r in records:
                try: data_list.append(json.loads(r))
                except: continue

        print(f"📋 총 {len(data_list)}개의 문서를 발견했습니다. 적재를 시작합니다.")

        # 데이터 루프 돌리기
        for data in data_list:
            if not data or "doc_id" not in data:
                continue
                
            # 중복 적재 방지
            existing_chunk = db.query(Notice).filter(Notice.chunk_id == data["doc_id"]).first()
            if existing_chunk:
                continue
            
            print(f"🔮 임베딩 생성 중 ➡️ {data.get('title', '정보')} ({data['doc_id']})")
            
            content_text = data.get("text")
            if not content_text:
                continue
                
            # OpenAI 임베딩 생성
            vector_data = get_embedding(content_text)
            meta = data.get("metadata", {})
            
            new_chunk = Notice(
                chunk_id=data["doc_id"],  
                doc_id=data["doc_id"],
                url=data.get("url"),
                title=data.get("title", "정보 없음"),
                page_type=data.get("page_type", "contents"),
                source=data.get("source", "saha.go.kr"),
                menu_path=data.get("menu_path", []),
                
                chunk_text=content_text,
                chunk_index=data.get("chunk_index", 0),
                embedding=vector_data,
                
                major=meta.get("major", ""),
                minor=meta.get("minor", ""),
                context=meta.get("context", "")
            )
            db.add(new_chunk)
            count += 1
            
            if count % 10 == 0:
                db.commit()
                print(f"💾 중간 저장 완료 ({count}개 완료...)")
        
        db.commit()
        print(f"\n✅ [성공] 총 {count}개의 데이터가 완벽하게 벡터 DB에 적재되었습니다!")
        
    except Exception as e:
        print(f"🔥 적재 중 크리티컬 에러 발생: {e}")
        db.rollback()
    finally:
        db.close()
        
if __name__ == "__main__":
    import_chunks()