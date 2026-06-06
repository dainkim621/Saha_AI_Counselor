import json
import os
import hashlib
from datetime import datetime

# [1] 전역 경로 설정 (실제 파일 위치에 맞게 세팅)
DATA_DIR = "data"
OUTPUT_JSONL = os.path.join(DATA_DIR, "processed", "saha_clean_chunks.jsonl")
OUTPUT_HTML = os.path.join(DATA_DIR, "processed", "saha_review_dashboard.html")

# ---------------------------------------------------------------------------
# [2] 각 크롤러 파일 별 함수 분리 및 전처리 로직
# ---------------------------------------------------------------------------

# 전역 중복 차단기는 함수 외부(모듈 최상위)에 선언해 두어야 
# 모든 문서를 돌면서 웹사이트 전역 중복을 거를 수 있습니다.
seen_texts = set()

def process_general_docs(doc):
    """
    1. 일반 웹페이지 정밀 처리 함수 (마스터 파이프라인 연동 버전)
    - 이제 file_path 대신 마스터가 읽어준 단일 doc(딕셔너리)을 인자로 받습니다.
    - chunks.append 대신, 이 문서 안에서 정제된 순수 데이터 리스트를 return 합니다.
    """
    refined_sections = []  # 이 문서 안에서 살아남은 알맹이 데이터들을 담을 임시 바구니
    
    doc_id = doc.get("doc_id")
    title = doc.get("title", "정보 안내")
    url = doc.get("url")
    
    # 1. 바로 가기 링크 맵 구성
    link_map = {}
    for link in doc.get("shortcut_links", []):
        link_text = link.get("text", "").strip()
        link_url = link.get("url", "").strip()
        if link_text and link_url:
            link_map[link_text] = link_url

    # 2. 한 페이지 안에 들어있는 여러 section을 하나씩 검사
    for sec in doc.get("sections", []):
        heading_path = sec.get("heading_path", [])
        block_type = sec.get("block_type", "")
        sec_text = sec.get("text", "").strip()
        
        # 기본 예외 처리 및 만족도 조사 박스 제거
        if block_type == "full_text_backup" or len(sec_text) < 15 or "research_box" in sec_text:
            continue
        
        # 접근성용 중복 표 데이터 제거 (| 기호 3개 이상)
        if sec_text.count("|") >= 3:
            continue
        
        # 공백 제거 후 전역 중복 검사
        norm_text = "".join(sec_text.split())
        
        if norm_text in seen_texts:
            continue
        
        # 부분 중복 및 포섭 관계 검사
        is_duplicate = False
        for existing_norm in seen_texts:
            if norm_text in existing_norm:
                is_duplicate = True
                break
            
        if is_duplicate:
            continue
        
        # 중복 검사 통과 시 차단기에 등록
        seen_texts.add(norm_text)
        
        # 마크다운 링크 치환
        for text_key, url_val in link_map.items():
            if text_key in sec_text and f"({url_val})" not in sec_text:
                sec_text = sec_text.replace(text_key, f"[{text_key}]({url_val})")

        # 마크다운 제목 구성
        sub_title = " > ".join(heading_path) if heading_path else title
        refined_text = f"# {sub_title}\n\n{sec_text}"
        
        # 마스터 파이프라인이 처리할 수 있도록 딱 필요한 "순수 알맹이 딕셔너리"만 만들어 담습니다.
        refined_sections.append({
            "title": sub_title,
            "page_type": "일반안내(contents)",
            "text": refined_text
        })
                
    return refined_sections  # 정제된 알맹이 리스트를 마스터에게 반환합니다.

def process_civil_forms(form):
    """2. 민원안내 서식 (saha_civil_forms.jsonl) 처리 함수
    - 민원안내 데이터는 본문 내용이 길고 상세한 경우가 많아서, 청크 단위를 '민원 하나'로 잡아서 최대한 원문을 보존하는 방향으로 전처리 합니다."""
    # 최소글자 수 80 못넘기면 마스터가 무시하도록 None 리턴
    if len(form.get("text", "")) < 80: 
        return None
    
    title = form.get("title", "민원 안내")
    dept = form.get("department", "해당부서")
    phone = form.get("phone", "안내번호")
    
    # 1. 원본 데이터의 모든 필드를 빠짐없이 안전하게 가져옵니다.
    req_docs = form.get("required_documents", "").strip()
    place = form.get("submission_place", "").strip()
    criteria = form.get("review_criteria", "").strip()
    workflow = form.get("workflow", "").strip()
    
    # 질문하신 핵심 3가지 필드 처리
    notes = form.get("notes", "").strip()          # 유의사항
    appeal = form.get("appeal", "").strip()        # 이의신청
    etc = form.get("etc", "").strip()              # 기타
    
    # 2. 텍스트 조립 (데이터가 없으면 '내용 없음' 혹은 '정보 없음'으로 처리)
    text_lines = [
        f"제목: {title}",
        f"담당부서: {dept} (문의처: {phone})",
        f"처리기간: {form.get('processing_period', '지체 없이')} | 수수료: {form.get('fee', '없음')}",
        f"제출처: {place if place else '해당 부서 및 동 행정복지센터'}",
        f"\n[구비서류 및 필요서류]\n{req_docs if req_docs else '정보 없음'}",
        f"\n[행정기관 심사 및 자격 기준]\n{criteria if criteria else '내용 없음'}",
        f"\n[업무 처리 흐름]\n{workflow if workflow else '정보 없음'}",
        
        # 데이터가 비어있어도 구조가 유지되도록 확실하게 매핑
        f"\n[유의사항]\n{notes if notes else '내용 없음'}",
        f"\n[이의신청 방법]\n{appeal if appeal else '내용 없음'}",
        f"\n[기타 사항]\n{etc if etc else '내용 없음'}"
    ]
    
    full_text = "\n".join(text_lines)
    
    # 3. 최종 청크 바구니에 담기
    return {
        "title": title,
        "page_type": "민원서식(civil_form)",
        "text": full_text
    }
            
    return chunks

def process_bid_notices(bid):
    """3. 입찰공고 (saha_bid_docs.jsonl) 처리 함수 (구조화 및 노이즈 제거 버전)"""
    
    title = bid.get("title", "입찰공고")
    
    # 1. 첨부파일 목록 정리 (리스트 형태인 attachments에서 파일명만 뽑아오기)
    attachments = bid.get("attachments", [])
    file_names = [file.get("file_name") for file in attachments if file.get("file_name")]
    attachments_str = ", ".join(file_names) if file_names else "없음"
    
    # 2. 본문(body)에서 기계적으로 긁힌 상단 메뉴 노이즈 제거하고 핵심 개요만 추출 시도
    body_raw = bid.get("body", "").strip()
    
    # 만약 '1. 공사개요' 또는 '1. 용역개요' 처럼 실무 내용이 시작되는 부분을 찾으면 
    # 그 전까지의 크롤링 껍데기 문장들은 과감히 잘라내 가독성을 높임.
    split_keyword = ""
    if "1. 공사개요" in body_raw:
        split_keyword = "1. 공사개요"
    elif "1. 용역개요" in body_raw:
        split_keyword = "1. 용역개요"
    elif "1. 공고대상" in body_raw:
        split_keyword = "1. 공고대상"
        
    if split_keyword:
        content_body = split_keyword + body_raw.split(split_keyword)[-1]
    else:
        content_body = body_raw # 키워드가 없다면 원본 본문 유지
    
    # 3. LLM과 인간이 모두 보기 편한 입찰공고용 표준 포맷으로 조립
    text_lines = [
        f"공고명: {title}",
        f"공고번호: {bid.get('notice_no', '번호없음')}",
        f"구분: {bid.get('notice_type', '공고')}",
        f"담당부서: {bid.get('department', '재무과')} (문의처: {bid.get('phone', '번호없음')})",
        f"등록일자: {bid.get('date', '정보없음')}",
        f"첨부문서: {attachments_str}",
        f"\n[사업 및 공고 상세내용]\n{content_body}"
    ]
    
    refined_text = "\n".join(text_lines)
    
    # 4. 굳이 쪼갤 필요 없이 하나의 공고당 하나의 청크로 저장
    return {
        "title": f"입찰정보 - {title}",
        "page_type": "입찰공고(bid_notice)",
        "text": refined_text
    }
            
    return chunks

def process_waste_guides(waste):
    """
    4. 폐기물 안내 (saha_waste_docs.jsonl) 처리 함수 (일반 문서 스타일 경로 빌드 버전)
    - 원본 데이터의 menu_path와 heading_path를 조합하여
      [대분류 > 중분류 > 소분류 > 소제목] 형태의 표준 가이드라인 본문을 생성합니다.
    """
    refined_chunks = []
    
    title = waste.get("title", "폐기물 안내")
    sections = waste.get("sections", [])
    
    # 1. 원본 크롤러 데이터에 있는 대메뉴 경로 추출 및 정제
    # 예: ["분야별정보", "환경/청소", "폐기물", "생활폐기물처리안내", "생활쓰레기 배출요령"]
    raw_menu_path = waste.get("menu_path", [])
    
    # 챗봇 답변용으로 너무 광범위한 상위 메뉴('분야별정보', '환경/청소')는 
    # 가독성을 위해 제외하고 필터링할 수 있습니다. (원치 않으시면 그냥 raw_menu_path 쓰셔도 됩니다!)
    filtered_menu = [m for m in raw_menu_path if m not in ["분야별정보", "환경/청소"]]
    
    # 기본 메뉴 경로 문자열 빌드 (예: "폐기물 > 생활폐기물처리안내 > 생활쓰레기 배출요령")
    base_path_str = " > ".join(filtered_menu) if filtered_menu else title

    # 챗봇에게 혼란을 주는 쓰레기 단어 차단 리스트
    junk_words = ["Home", ">", "열기", "닫기", "인쇄하기"]
    
    for section in sections:
        raw_text = section.get("text", "").strip()
        if not raw_text:
            continue
            
        # 2. 본문 노이즈 필터링
        lines = raw_text.split("\n")
        filtered_lines = [
            l.strip() for l in lines 
            if l.strip() and not any(junk in l for junk in junk_words)
        ]
        
        if not filtered_lines:
            continue
            
        clean_section_text = "\n".join(filtered_lines)
        
        # 3. 🌟 핵심: 일반 문서 스타일로 최종 상세 계층 경로 조립
        # 현재 섹션의 heading_path가 있으면 중복을 피해 마지막 소제목들을 추출합니다.
        heading_path = section.get("heading_path", [])
        
        # 메뉴 경로와 섹션 소제목 경로를 융합하여 덩어리를 만듭니다.
        # 중복 방지를 위해 heading_path의 요소 중 base_path_str에 없는 참신한 소제목만 뒤에 붙여줍니다.
        unique_headings = [h for h in heading_path if h not in filtered_menu]
        
        if unique_headings:
            full_hierarchy = f"{base_path_str} > {' > '.join(unique_headings)}"
        else:
            full_hierarchy = base_path_str
        
        # 4. 💻 [제목 > 중제목 > 소제목] 포맷으로 본문(chunk_text) 데이터 완성!
        text_lines = [
            f"[{full_hierarchy}]",  # 👈 제일 윗줄에 대괄호 경로 명시! (일반 문서 양식 싱크)
            clean_section_text
        ]
        full_chunk_text = "\n".join(text_lines)
        
        # 5. 마스터에게 토스할 바구니에 담기
        refined_chunks.append({
            "title": f"{title} - {heading_path[-1] if heading_path else '상세'}",
            "page_type": "waste_guide",
            "text": full_chunk_text
        })
        
    return refined_chunks if refined_chunks else None


# ---------------------------------------------------------------------------
# [3] 4개 통합 청크
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
        
        # 🌟 벡터 임베딩 (초기 전처리 단계에서는 None이었다가, 임베딩 모델 거친 후 채워집니다)
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
        
        # 🌟 2. 질문하신 '파일이 없을 때 안전하게 넘어가는 예외 처리'를 여기서 일괄 진행합니다!
        if not os.path.exists(file_path):
            print(f"⚠️ 경고: {file_path} 파일이 존재하지 않아 건너뜁니다.")
            continue # 다음 파일 처리로 패스!
            
        # 파일이 안전하게 존재하는 게 확인되었으니 open 합니다.
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
                
                #전처리 함수가 None을 리턴할 때 (예: 민원서식이 너무 짧아서 무시된 경우) 대비한 안전장치
                if refined_data is None:
                    continue
                
                # 리스트 형태로 만들어서 마스터 바구니에 차곡차곡 append
                if not isinstance(refined_data, list):
                    refined_data = [refined_data]
                    
                for idx, item in enumerate(refined_data):
                    if item is None:
                        continue
                    # 🌟 1. 원본 데이터(doc)에 있는 모든 유용한 메타데이터를 기본 베이스로 장착!
                    base_meta = {
                        "url": doc.get("url"),
                        "published_at": doc.get("published_at") or doc.get("date"),
                        "views": doc.get("views", 0),
                        "menu_path": doc.get("menu_path", []),
                        
                        # 👉 말씀하신 대로 원본에 있는 부서와 전번을 마스터가 직접 챙깁니다!
                        "department": doc.get("department"),
                        "phone": doc.get("phone")
                    }
                    
                    # 🌟 2. 전처리 함수가 다듬은 알맹이(title, text, page_type 등)를 위에 덮어씁니다.
                    base_meta.update(item)
                    
                    # 🌟 3. 최종 통합 객체 조립
                    chunk_obj = create_chunk_object(
                        doc_id=doc.get("doc_id"),
                        chunk_index=idx,
                        **base_meta  # 완벽하게 조립된 메타데이터 뭉치를 던집니다!
                    )
                    final_db_ready_chunks.append(chunk_obj)   
                                        
    return final_db_ready_chunks
# ---------------------------------------------------------------------------
# [4] 시각화 HTML 생성 전용 함수
# ---------------------------------------------------------------------------
def generate_html_dashboard(chunks, output_path):
    """수집된 청크 리스트를 바탕으로 인간 검수용 대시보드 HTML을 렌더링하는 함수"""
    html_content = f"""<!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>사하구청 챗봇 RAG 데이터 검수 대시보드</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            header {{ background: linear-gradient(135deg, #2c3e50, #2980b9); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; }}
            header h1 {{ margin: 0; font-size: 28px; }}
            .stats {{ display: inline-block; background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; margin-top: 10px; font-weight: bold; }}
            .card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; border-left: 6px solid #2980b9; }}
            .card.civil {{ border-left-color: #27ae60; }}
            .card.bid {{ border-left-color: #e67e22; }}
            .card.waste {{ border-left-color: #8e44ad; }}
            .meta-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px dashed #eee; padding-bottom: 8px; }}
            .doc-id {{ font-family: monospace; font-weight: bold; color: #7f8c8d; background: #eaedf1; padding: 3px 8px; border-radius: 4px; }}
            .badge {{ padding: 4px 10px; border-radius: 20px; color: white; font-size: 12px; font-weight: bold; background-color: #2980b9; }}
            .badge.civil {{ background-color: #27ae60; }}
            .badge.bid {{ background-color: #e67e22; }}
            .badge.waste {{ background-color: #8e44ad; }}
            .title {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
            .content-box {{ background-color: #fafbfc; border: 1px solid #e1e4e8; border-radius: 6px; padding: 15px; white-space: pre-wrap; line-height: 1.6; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>사하구청 AI 상담사 고우니 - RAG 청크 검수 대시보드 🐳</h1>
                <div class="stats">📋 정제 완료된 총 청크 수: {len(chunks)}개</div>
            </header>
            <div class="list">
    """
    for chunk in chunks:
        ptype = chunk.get("page_type", "")
        card_cls, badge_cls = "card", "badge"
        
        # 💡 [1] 새로 통합한 page_type 키워드 조건에 맞게 CSS 테마 매칭
        if "civil" in ptype or "민원" in ptype: 
            card_cls, badge_cls = "card civil", "badge civil"
        elif "bid" in ptype or "입찰" in ptype: 
            card_cls, badge_cls = "card bid", "badge bid"
        elif "waste" in ptype or "폐기물" in ptype: 
            card_cls, badge_cls = "card waste", "badge waste"
            
        # 💡 [2] chunk.get('text') 대신 스키마와 통일한 chunk_text를 안전하게 가져옴
        text_content = chunk.get("chunk_text", "") or ""
        safe_text = text_content.replace('<', '&lt;').replace('>', '&gt;')
            
        html_content += f"""
                <div class="{card_cls}">
                    <div class="meta-row">
                        <span class="doc-id">ID: {chunk.get('chunk_id')}</span>
                        <span class="{badge_cls}">{ptype}</span>
                    </div>
                    <div class="title">{chunk.get('title')}</div>
                    <a href="{chunk.get('url')}" target="_blank" style="font-size:13px; color:#3498db; text-decoration:none;">🔗 원본 구청 페이지</a>
                    <div class="content-box">{safe_text}</div>
                </div>
        """
    html_content += "</div></div></body></html>"
    
    # 디렉토리가 없으면 생성 후 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
# ---------------------------------------------------------------------------
# [5] 메인 실행 컨트롤러 
# ---------------------------------------------------------------------------
def main():
    print("🚀 크롤링 데이터 전처리 및 시각화 빌드 가동...")
    
    # 1) 각 전처리 파트별 RAW 파일 경로들을 하나의 딕셔너리로 묶어줍니다.
    file_paths = {
        "general": os.path.join(DATA_DIR, "raw", "saha_docs.jsonl"),
        "civil": os.path.join(DATA_DIR, "raw", "saha_civil_forms.jsonl"),
        "bid": os.path.join(DATA_DIR, "raw", "saha_bid_docs.jsonl"),
        "waste": os.path.join(DATA_DIR, "raw", "saha_waste_docs.jsonl"),
    }
    
    # 2) [핵심 변화] 마스터 파이프라인 함수를 딱 한 번만 호출합니다.
    # 이 함수 안에서 파일 유무 체크, 파일 열기, 각 파트별 전처리(다듬기), 
    # 그리고 최종 create_chunk_object와 append까지 올인원으로 처리되어 꽉 찬 바구니가 리턴됩니다.
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
    print(f"🖥️  [2단계 완수] 인간 검수용 대시보드 웹 뷰 완료 -> {OUTPUT_HTML}")
    print("✨ 모든 파이프라인이 성공적으로 완결되었습니다! ^-^")


if __name__ == "__main__":
    main()
    