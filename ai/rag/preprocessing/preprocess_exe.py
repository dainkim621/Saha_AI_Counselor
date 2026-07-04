import json
import os
import hashlib
from datetime import datetime
from .domains import process_general_docs, process_civil_forms, process_bid_notices, process_waste_guides, process_passport_forms
from .review import generate_html_dashboard
# ---------------------------------------------------------------------------
# [1] 전역 경로 설정 (실제 파일 위치에 맞게 세팅)
# ---------------------------------------------------------------------------
DATA_DIR = "data"
OUTPUT_JSONL = os.path.join(DATA_DIR, "processed", "saha_clean_chunks.jsonl")
OUTPUT_HTML = os.path.join(DATA_DIR, "processed", "saha_review_dashboard.html")

# ---------------------------------------------------------------------------
# [3] 상위 마스터 함수 
# ---------------------------------------------------------------------------

def create_chunk_object(doc_id, chunk_index, **kwargs):
    """
    Notice DB 스키마 구조와 1:1 매핑되는 통합 청크 객체 생성 함수.
    전처리 함수가 리턴한 딕셔너리 데이터(**kwargs)를 풀어서 자동으로 조립합니다.
    """
    # 1. 텍스트 본문 추출 및 안전장치
    text_content = kwargs.get("text", "")
    if not text_content and "chunk_text" in kwargs:
        text_content = kwargs.get("chunk_text", "")
        
    text_content = text_content.strip() if text_content else ""

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
    모든 JSONL 파일 경로들을 받아서 안전하게 파일을 열고, 
    알맹이 데이터를 추출해 전처리 함수로 넘겨주는 마스터 파이프라인
    """
    # 4개 함수에 chunks 선언 대신 한번만 선언
    final_db_ready_chunks = []
    
    # file_paths_dict 예시: {"civil": "data/raw/saha_civil_forms.jsonl", "bid": "..."}
    for page_type, file_path in file_paths_dict.items():
        
        #  파일이 없을 때 안전하게 넘어가는 예외 처리
        if not os.path.exists(file_path):
            print(f"⚠️ 경고: {file_path} 파일이 존재하지 않아 건너뜁니다.")
            continue # 다음 파일 처리로 패스!
            
        # 파일이 안전하게 존재하는 게 확인되었으니 open
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip(): continue
                doc = json.loads(line.strip())
                
                # 전처리 
                if page_type == "general":
                    refined_data = process_general_docs(doc) # 리스트 혹은 단일 딕셔너리
                elif page_type == "waste":
                    refined_data = process_waste_guides(doc)
                elif page_type == "civil":
                    refined_data = process_civil_forms(doc)
                elif page_type == "bid":
                    refined_data = process_bid_notices(doc)
                elif page_type == "passport":
                    refined_data = process_passport_forms(doc)
                
                #전처리 함수가 None을 리턴할 때 (예: 민원서식이 너무 짧아서 무시된 경우) 대비한 안전장치
                if refined_data is None:
                    continue
                
                # 리스트 형태로 만들어서 마스터가 일관되게 처리할 수 있도록 함 (단일 딕셔너리도 리스트로 감싸기)
                if not isinstance(refined_data, list):
                    refined_data = [refined_data]
                    
                for idx, item in enumerate(refined_data):
                    if item is None:
                        continue
                    # (1) 원본 데이터(doc)에 있는 모든 유용한 메타데이터를 기본 베이스로 함
                    base_meta = {
                        "url": doc.get("url"),
                        "published_at": doc.get("published_at") or doc.get("date"),
                        "views": doc.get("views", 0),
                        "menu_path": doc.get("menu_path", []),
                        "department": doc.get("department"),
                        "phone": doc.get("phone")
                    }
                    
                    # (2) 전처리 함수가 다듬은 알맹이(title, text, page_type 등)를 위에 덮어씀
                    base_meta.update(item)
                    
                    # (3) 최종 통합 객체 조립
                    chunk_obj = create_chunk_object(
                        doc_id=doc.get("doc_id"),
                        chunk_index=idx,
                        **base_meta  # 조립된 메타데이터와 본문이 담긴 딕셔너리를 풀어서 전달
                    )
                    final_db_ready_chunks.append(chunk_obj)   
                                        
    return final_db_ready_chunks


# ---------------------------------------------------------------------------
# [5] 메인 실행 컨트롤러 
# ---------------------------------------------------------------------------
def main():
    print("🚀 크롤링 데이터 전처리 및 시각화 빌드 가동...")
    
    # (1) 각 전처리 파트별 RAW 파일 경로들을 하나의 딕셔너리로 묶어줍니다.
    # 원하는 파일 말고 다른 파일을 주석처리 해서 원하는 파일의 전처리 결과만 볼 수 있습니다. 
    file_paths = {
        #"general": os.path.join(DATA_DIR, "raw", "saha_docs.jsonl"),
        #"civil": os.path.join(DATA_DIR, "raw", "saha_civil_forms.jsonl"),
        #"bid": os.path.join(DATA_DIR, "raw", "saha_bid_docs.jsonl"),
        "waste": os.path.join(DATA_DIR, "raw", "saha_waste_docs.jsonl"),
        #"passport": os.path.join(DATA_DIR, "raw", "passport_forms.jsonl")
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


if __name__ == "__main__":
    main()
    