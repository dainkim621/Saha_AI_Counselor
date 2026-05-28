import json
import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from sqlalchemy.orm import Session

from app.database import SessionLocal, engine, Base
from app.models import Notice

load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

# OpenAI embedding 입력 초과 방지용
MAX_EMBED_TEXT_LEN = 5000
OVERLAP = 500


def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)

    return text.strip()


def split_for_embedding(text: str, max_len=MAX_EMBED_TEXT_LEN, overlap=OVERLAP):
    """
    OpenAI embedding 최대 토큰 초과 방지용 분할.
    문자 기준 5000자 정도면 text-embedding-3-small에서 안전하게 처리 가능.
    """
    text = clean_text(text)

    if not text:
        return []

    if len(text) <= max_len:
        return [text]

    chunks = []
    start = 0

    while start < len(text):
        end = start + max_len
        part = text[start:end].strip()

        if part:
            chunks.append(part)

        start += max_len - overlap

    return chunks


def get_embedding(text):
    response = client.embeddings.create(
        input=text,
        model="text-embedding-3-small",
    )
    return response.data[0].embedding


def import_chunks():
    print("🛠️ 테이블 확인 및 생성 중...")
    
    # ⚠️ 주의: 기존 데이터 테이블을 밀고 새로 만듭니다.
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()

    # 💡 수빈님이 새로 만든 예쁜 정제 묶음 파일 경로
    file_path = "data/processed/saha_clean_chunks.jsonl"

    if not os.path.exists(file_path):
        print(f"❌ 파일을 찾을 수 없습니다: {file_path}")
        return

    print("🚀 .jsonl 라인 단위 데이터 적재 및 OpenAI 벡터 변환 시작...")

    total_saved = 0
    total_docs = 0

    try:
        # 💡 [핵심 변경 포인트] 파일을 통째로 loads하지 않고, 한 줄씩 iterator로 읽어 메모리를 아낍니다.
        with open(file_path, "r", encoding="utf-8") as f:
            for line_idx, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue  # 빈 줄은 가볍게 패스

                try:
                    data = json.loads(line)
                except json.JSONDecodeError as je:
                    print(f"⚠️ {line_idx}번째 라인 파싱 실패 (건너뜀): {je}")
                    continue

                if not data or "doc_id" not in data:
                    continue

                total_docs += 1

                # 💡 전처리 단계에서 정제해 둔 'text' 필드를 우선적으로 획득
                original_text = data.get("text") or data.get("chunk_text") or ""

                if not original_text:
                    continue

                # 5000자가 넘어갈 경우를 대비한 2차 가드 분할
                split_texts = split_for_embedding(original_text)

                print(
                    f"🔮 [{total_docs}] 임베딩 생성 중 ➡️ "
                    f"{data.get('title', '정보')} ({data['doc_id']}) "
                    f"/ 분할 {len(split_texts)}개"
                )

                meta = data.get("metadata", {}) or {}

                for split_idx, content_text in enumerate(split_texts):
                    try:
                        vector_data = get_embedding(content_text)
                    except Exception as e:
                        print(
                            f"⚠️ 임베딩 실패: {data.get('title', '정보')} "
                            f"split={split_idx}, 길이={len(content_text)} / {e}"
                        )
                        continue

                    # 고유한 chunk_id 생성
                    chunk_id = f"{data['doc_id']}_{split_idx}"

                    new_chunk = Notice(
                        chunk_id=chunk_id,
                        doc_id=data["doc_id"],
                        url=data.get("url"),
                        title=data.get("title", "정보 없음"),
                        page_type=data.get("page_type", "contents"),
                        source=data.get("source", "saha.go.kr"),
                        menu_path=data.get("menu_path", []),

                        chunk_text=content_text,
                        chunk_index=split_idx,
                        embedding=vector_data,

                        major=meta.get("major", ""),
                        minor=meta.get("minor", ""),
                        context=meta.get("context", ""),
                    )

                    db.add(new_chunk)
                    total_saved += 1

                    # 10개 단위로 안전하게 디비 저장 및 출력 로그 찍기
                    if total_saved % 10 == 0:
                        db.commit()
                        print(f"💾 DB 커밋 완료 ({total_saved}개 저장)")

        # 남은 데이터 최종 커밋
        db.commit()

        print("\n✅ .jsonl 데이터 적재 완벽 성공!")
        print(f"- 읽어들인 원본 청크 수: {total_docs}")
        print(f"- pgvector DB에 최종 세이브된 chunk 수: {total_saved}")

    except Exception as e:
        print(f"🔥 적재 중 크리티컬 에러 발생: {e}")
        db.rollback()

    finally:
        db.close()


if __name__ == "__main__":
    import_chunks()