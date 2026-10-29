import json
import os
import hashlib
from datetime import datetime
from langchain_text_splitters import RecursiveCharacterTextSplitter  # 청크 더 ㅈ조갬

from .domains import process_general_docs, process_civil_forms, process_bid_notices, process_waste_guides, process_passport_forms
from .review import generate_html_dashboard

'''
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1200, 
    chunk_overlap=50 
)
'''
def split_text_without_loss(text, chunk_size=1200, chunk_overlap=50):
    """
    원본 문자를 삭제하지 않고 분할.
    인접 청크 사이에 50자 중복 유지.
    """
    if not text:
        return []

    if not 0 <= chunk_overlap < chunk_size:
        raise ValueError("chunk_overlap은 chunk_size보다 작아야 합니다.")

    chunks = []
    step = chunk_size - chunk_overlap

    for start in range(0, len(text), step):
        chunk = text[start:start + chunk_size]

        if chunk:
            chunks.append(chunk)

        if start + chunk_size >= len(text):
            break

    return chunks

# ========================================================================
# [1] 전역 경로 설정 (실제 파일 위치에 맞게 세팅)
# ========================================================================
DATA_DIR = "data"
OUTPUT_JSONL = os.path.join(DATA_DIR, "processed", "saha_clean_chunks.jsonl") # 전처리 파일
OUTPUT_HTML = os.path.join(DATA_DIR, "processed", "saha_review_dashboard.html") # 전처리 검수용 파일

# ========================================================================
# [2] 메인 실행 컨트롤러 
# ========================================================================
def main():
    print("🚀 크롤링 데이터 전처리 및 시각화 빌드 가동...")
    
    # (1) 각 전처리 파트별 RAW 파일 경로들을 하나의 딕셔너리로 묶어줍니다.
    # 원하는 파일 말고 다른 파일을 주석처리 해서 원하는 파일의 전처리 결과만 볼 수 있습니다. 
    file_paths = {
        "general": os.path.join(DATA_DIR, "raw", "saha_docs.jsonl"),
        "civil": os.path.join(DATA_DIR, "raw", "saha_civil_forms.jsonl"),
        "bid": os.path.join(DATA_DIR, "raw", "saha_bid_docs.jsonl"),
        "waste": os.path.join(DATA_DIR, "raw", "saha_waste_docs.jsonl"),
        "passport": os.path.join(DATA_DIR, "raw", "passport_forms.jsonl")
    }
    
    # (2) 마스터 파이프라인 함수 호출 - 이 함수 안에서 5개 전처리 함수가 모두 호출되어 각 파일별로 알맹이 데이터가 추출되고,
    # 이 함수 안에서 파일 유무 체크, 파일 열기, 각 파트별 전처리(다듬기), 
    # 그리고 최종 create_chunk_object와 append까지 처리됩니다.
    all_chunks = run_preprocessing_pipeline(file_paths)

    # 3) 파일 저장 처리 (JSONL)
    if not all_chunks:
        print("⚠️ 수집된 데이터 청크가 0개입니다. 소스 파일들의 경로('data/')나 위치를 다시 확인해주세요!")
        return

    os.makedirs(os.path.dirname(OUTPUT_JSONL), exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out_f:
        for chunk in all_chunks:
            out_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            
    print(f"✅ [1단계 완수] 통합 적재용 JSONL 완료 -> {OUTPUT_JSONL} ({len(all_chunks)}개 청크)")

    # 4) 대시보드 웹 페이지 생성 함수 호출
    generate_html_dashboard(all_chunks, OUTPUT_HTML)
    print(f"🖥️  [2단계 완수] 검수용 대시보드 웹 뷰 완료 -> {OUTPUT_HTML}")
    print("✨ 모든 파이프라인이 성공적으로 완결되었습니다! ^-^")
    
# ========================================================================
# [2] 상위 마스터 함수 
# =======================================================================

def create_chunk_object(doc_id, chunk_index, **kwargs):
    """
    Notice DB 스키마 구조와 1:1 매핑되는 통합 청크 객체 생성 함수.
    전처리 함수가 리턴한 딕셔너리 데이터(**kwargs)를 풀어서 자동으로 조립합니다.
    """
    # 1. 텍스트 본문 추출 및 원본 보존
    text_content = kwargs.get("text")

    if text_content is None:
        text_content = kwargs.get("chunk_text", "")

    if text_content is None:
        text_content = ""

    if not isinstance(text_content, str):
        text_content = str(text_content)

    # 원본 보존을 위해 strip()을 사용하지 않음

    # 2. 내용 변경 감지용 MD5 해시값 생성 (주석 해제 대비 자동 생성)
    text_hash = hashlib.md5(text_content.encode("utf-8")).hexdigest() if text_content else None

    # 3. Notice 스키마 컬럼명과 1:1 매핑되는 딕셔너리 빌드
    chunk = {
        # 고유 식별자 및 인덱스
        "chunk_id": f"{doc_id}_{chunk_index}", # 스키마 주석의 예시(doc_id_0) 규칙 반영
        "doc_id": doc_id,
        "chunk_index": chunk_index,
        
        # 메타데이터 (kwargs에서 있으면 가져오고, 없으면 기본값 매칭)
        "url": kwargs.get("url", ""),
        "source": kwargs.get("source", "saha.go.kr"),
        "title": kwargs.get("title", "정보 안내"),
        "author": kwargs.get("department") or kwargs.get("author", "담당부서 미지정"),
        
        # 날짜 및 수치
        "published_at": kwargs.get("published_at", None), # 전처리에서 Date 객체나 YYYY-MM-DD 형식으로 넣어줄 예정
        "views": kwargs.get("views", 0),
        
        # 계층 정보 및 분류
        "menu_path": kwargs.get("menu_path", []),
        "page_type": kwargs.get("page_type", None),
        "major": kwargs.get("major", None),
        "minor": kwargs.get("minor", None),
        "context": kwargs.get("context", None),
        
        # 데이터 본체 및 변경 감지용 해시
        "chunk_text": text_content,
        "text_hash": text_hash,  # 주석 푸실 때를 대비해 미리 매핑해 둡니다.
        
        # 벡터 임베딩 (초기 전처리 단계에서는 None이었다가, 임베딩 모델 거친 후 채워짐)
        "embedding": kwargs.get("embedding", None)
    }
    
    return chunk


def run_preprocessing_pipeline(file_paths_dict):
    """
    전체 JSONL 데이터를 도메인별로 전처리하고 청킹하는 함수.

    개선 사항:
    1. 기존 5개 도메인 전처리 유지
    2. 원본 텍스트를 임의로 strip()하여 삭제하지 않음
    3. 문자 단위 청킹으로 텍스트 손실 방지
    4. 청킹 후 원본 복원 검증
    5. 문서별 chunk_index 순차 생성
    """

    final_db_ready_chunks = []

    # 동일 doc_id가 다른 크롤러에서 등장해도
    # chunk_index가 이어지도록 관리
    doc_chunk_counters = {}

    processors = {
        "general": process_general_docs,
        "civil": process_civil_forms,
        "bid": process_bid_notices,
        "waste": process_waste_guides,
        "passport": process_passport_forms
    }

    for page_type, file_path in file_paths_dict.items():

        if not os.path.exists(file_path):
            print(f"⚠️ 파일 없음: {file_path}")
            continue

        print(f"\n📂 전처리 시작: {file_path}")

        processed_docs = 0
        generated_chunks = 0

        with open(file_path, "r", encoding="utf-8") as f:

            for line_number, line in enumerate(f, start=1):

                if not line.strip():
                    continue

                doc = json.loads(line)

                processor = processors.get(page_type)

                if processor is None:
                    raise ValueError(
                        f"지원하지 않는 도메인: {page_type}"
                    )

                # 1. 도메인별 전처리
                refined_data = processor(doc)

                if refined_data is None:
                    continue

                if not isinstance(refined_data, list):
                    refined_data = [refined_data]

                doc_id = doc.get("doc_id")

                if not doc_id:
                    raise ValueError(
                        f"doc_id 누락: {file_path}:{line_number}"
                    )

                chunk_counter = doc_chunk_counters.get(doc_id, 0)

                # 2. 전처리 데이터 순회
                for item in refined_data:

                    if item is None:
                        continue

                    base_meta = {
                        "url": doc.get("url"),
                        "published_at": (
                            doc.get("published_at")
                            or doc.get("date")
                        ),
                        "views": doc.get("views", 0),
                        "menu_path": doc.get("menu_path", []),
                        "department": doc.get("department"),
                        "phone": doc.get("phone")
                    }

                    base_meta.update(item)

                    # 3. 전처리된 원문 가져오기
                    raw_text = (
                        base_meta.get("text")
                        or base_meta.get("chunk_text")
                        or ""
                    )

                    if not isinstance(raw_text, str):
                        raw_text = str(raw_text)

                    if not raw_text:
                        continue

                    # 4. 손실 없는 문자 단위 청킹
                    split_texts = split_text_without_loss(
                        raw_text,
                        chunk_size=1200,
                        chunk_overlap=50
                    )

                    # 5. 청크를 다시 결합하여 원문 보존 검증
                    if split_texts:

                        reconstructed = split_texts[0]

                        for chunked_text in split_texts[1:]:
                            reconstructed += chunked_text[50:]

                        if reconstructed != raw_text:
                            raise ValueError(
                                "청킹 중 원문 손실 발생!\n"
                                f"문서: {doc.get('title')}\n"
                                f"doc_id: {doc_id}\n"
                                f"도메인: {page_type}"
                            )

                    # 6. 최종 청크 객체 생성
                    for chunked_text in split_texts:

                        chunk_meta = base_meta.copy()

                        chunk_meta["text"] = chunked_text
                        chunk_meta["chunk_text"] = chunked_text

                        chunk_obj = create_chunk_object(
                            doc_id=doc_id,
                            chunk_index=chunk_counter,
                            **chunk_meta
                        )

                        final_db_ready_chunks.append(chunk_obj)

                        chunk_counter += 1
                        generated_chunks += 1
                doc_chunk_counters[doc_id] = chunk_counter
                processed_docs += 1

        print(
            f"✅ {page_type} 전처리 완료 | "
            f"문서: {processed_docs}개 | "
            f"청크: {generated_chunks}개"
        )

    print(
        f"\n🎉 전체 전처리 완료! "
        f"총 {len(final_db_ready_chunks)}개 청크 생성"
    )

    return final_db_ready_chunks

if __name__ == "__main__":
    main()
    