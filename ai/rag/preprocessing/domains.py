import os
from .handler import check_merge_condition, build_merged_chunk_text

# ---------------------------------------------------------------------------
# [2] 하위 전처리 함수 정의 (문서 유형별로 세분화)
# ---------------------------------------------------------------------------

# 전역 중복 차단기는 함수 외부(모듈 최상위)에 선언해 두어야 
# 모든 문서를 돌면서 웹사이트 전역 중복을 거를 수 있음.
# seen_texts = set()                                           #잠깐 주석 
def process_general_docs(doc):
    """
    일반안내 문서의 원본 정보 보존 전처리.

    - 모든 비어 있지 않은 sections 보존
    - full_text_backup 보존
    - 표 데이터 보존
    - 짧은 텍스트 보존
    - 문서 간 중복 제거하지 않음
    - 원본 텍스트를 임의로 삭제하거나 치환하지 않음
    """

    title = doc.get("title") or "정보 안내"
    page_type = doc.get("page_type") or "contents"

    # 직원 업무 안내는 별도 text 필드 사용
    if page_type == "staff":
        staff_text = doc.get("text") or ""

        if not staff_text.strip():
            return []

        return [{
            "title": title,
            "page_type": "staff",
            "text": staff_text,
            "author": doc.get("department") or doc.get("author")
        }]

    refined_sections = []
    sections = doc.get("sections") or []

    # 원본 sections를 순서대로 보존
    for sec in sections:
        sec_text = sec.get("text") or ""

        if not sec_text.strip():
            continue

        block_type = sec.get("block_type") or ""
        heading_path = sec.get("heading_path") or []

        # 백업과 상세 섹션을 모두 보존
        if block_type == "full_text_backup":
            sub_title = title
        else:
            sub_title = (
                " > ".join(str(h) for h in heading_path)
                if heading_path else title
            )

        refined_sections.append({
            "title": sub_title,
            "page_type": "일반안내(contents)",
            "text": f"# {sub_title}\n\n{sec_text}"
        })

    # sections가 없을 때 최상위 text 사용
    if not refined_sections:
        raw_text = doc.get("text") or ""

        if raw_text.strip():
            refined_sections.append({
                "title": title,
                "page_type": "일반안내(contents)",
                "text": f"# {title}\n\n{raw_text}"
            })

    return refined_sections

    
def process_civil_forms(form):
    """2. 민원안내 서식 (saha_civil_forms.jsonl) 처리 함수
    - 민원안내 데이터는 본문 내용이 길고 상세한 경우가 많아서, 청크 단위를 '민원 하나'로 잡아서 최대한 원문을 보존하는 방향으로 전처리 합니다."""
    # 최소글자 수 80 못넘기면 마스터가 무시하도록 None 리턴
    if len(form.get("text", "")) < 80: 
        return None
    
    title = form.get("title", "민원 안내")
    dept = form.get("department", "해당부서")
    phone = form.get("phone", "안내번호")
    
    # 1. 원본 데이터의 모든 필드 가져오기
    req_docs = form.get("required_documents", "").strip()
    place = form.get("submission_place", "").strip()
    criteria = form.get("review_criteria", "").strip()
    workflow = form.get("workflow", "").strip()
    notes = form.get("notes", "").strip()          # 유의사항
    appeal = form.get("appeal", "").strip()        # 이의신청
    etc = form.get("etc", "").strip()              # 기타
    
    attachments = form.get("attachments", [])
    download_links_str = ""
    
    if attachments:
        download_links_str = "\n\n📄 **사하구청 원본 서식 다운로드**"
        for att in attachments:
            filename = att.get("filename", "첨부파일")
            file_url = att.get("file_url", "").strip()
            if file_url:
                # 마크다운 문법으로 링크를 심어줌.
                # 나중에 챗봇 화면에서 이 주소를 기반으로 다운로드 링킹이 작동
                download_links_str += f"\n- [{filename}]({file_url})"
                
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
    
    full_text = "\n".join(text_lines) + download_links_str
    
    
    # 3. 최종 청크 객체를 딕셔너리 형태로 만들어서 마스터에게 반환
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
    # 그 전까지의 크롤링 껍데기 문장들은 잘라내 가독성을 높임.
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
    
    # 4. 청킹 없이 하나의 공고당 하나의 청크로 저장
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
    # 가독성을 위해 제외하고 필터링
    filtered_menu = [m for m in raw_menu_path if m not in ["분야별정보", "환경/청소"]]
    
    # 기본 메뉴 경로 문자열 빌드 (예: "폐기물 > 생활폐기물처리안내 > 생활쓰레기 배출요령")
    base_path_str = " > ".join(filtered_menu) if filtered_menu else title

    # 챗봇에게 혼란을 주는 단어 차단 리스트
    junk_words = ["Home", ">", "열기", "닫기", "인쇄하기"]
    
    weekly_groups = {}
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
        
        # 3. 일반 문서 스타일로 최종 상세 계층 경로 조립
        # 현재 섹션의 heading_path가 있으면 중복을 피해 마지막 소제목들을 추출
        heading_path = section.get("heading_path", [])
        
        # 메뉴 경로와 섹션 소제목 경로를 합쳐서 덩어리를 만듬.
        # 중복 방지를 위해 heading_path의 요소 중 base_path_str에 없는 참신한 소제목만 뒤에 붙여줍니다.
        unique_headings = [h for h in heading_path if h not in filtered_menu]
        
        # 분리한 함수를 사용하여 병합 예외 대상인지 검사 
        if check_merge_condition(unique_headings):
            
            # 💡 [핵심 분기] 요일인지, 아니면 소파 같은 일반 항목인지 구분!
            last_item = unique_headings[-1]
            is_day_of_week = last_item in ["월", "화", "수", "목", "금", "토", "일"]
            
            if is_day_of_week:
                # 1. 요일 데이터: 기존 방식대로 마지막 요일 글자를 떼어내고 부모 경로만 사용
                parent_headings = unique_headings[:-1]
                current_unit = last_item  # 예: "월"
            else:
                # 2. 소파 같은 일반 데이터: 제목을 자르지 않고 전체 경로를 그대로 사용!
                parent_headings = unique_headings  # 👈 전체 유지!
                current_unit = last_item   # 예: "소파"
            
            if parent_headings:
                full_hierarchy = f"{base_path_str} > {' > '.join(parent_headings)}"
            else:
                full_hierarchy = base_path_str
                
            # 해당 상위 경로 그룹에 요일과 본문을 차곡차곡 누적 (청크 생성을 뒤로 미룸)
            if full_hierarchy not in weekly_groups:
                weekly_groups[full_hierarchy] = []
            weekly_groups[full_hierarchy].append((current_unit, clean_section_text))
        
        
        
        else:
            if unique_headings:
                full_hierarchy = f"{base_path_str} > {' > '.join(unique_headings)}"
            else:
                full_hierarchy = base_path_str
        
            # 4.  [제목 > 중제목 > 소제목] 포맷으로 본문(chunk_text) 완성
            text_lines = [
                f"# {full_hierarchy}",  # 👈 제일 윗줄에 대괄호 경로 명시! (일반 문서 양식 싱크)
                clean_section_text
            ]
            full_chunk_text = "\n".join(text_lines)
            
            # 5. 마스터에게 전달할 최종 청크 객체를 딕셔너리 형태로 만들어서 refined_chunks에 append
            refined_chunks.append({
                "title": full_hierarchy,
                "page_type": "waste_guide",
                "text": full_chunk_text
            })
            
    # ─── [for 루프 종료 후] ───
    # 루프를 돌며 모아놓았던 요일 그룹 데이터들을 일주일 단위 통합 청크로 만들어서 추가
    for parent_path, day_items in weekly_groups.items():
        # 분리해 둔 조립 함수 호출
        full_chunk_text = build_merged_chunk_text(parent_path, day_items)
        
        # 일주일 치가 통째로 들어간 단 하나의 청크 객체 생성
        refined_chunks.append({
            "title": parent_path,
            "page_type": "waste_guide",
            "text": full_chunk_text
        })
    return refined_chunks if refined_chunks else None

def process_passport_forms(pdf_doc):
    title = pdf_doc.get("title", "여권 서식 안내")
    raw_text = pdf_doc.get("text", "").strip()
    
    # 원본 데이터 구조에 있는 attachments 배열에서 실제 파일명을 가져오기
    attachments = pdf_doc.get("attachments", [])
    file_name = attachments[0].get("name") if attachments else f"{title}.pdf"
    
    # FastAPI 마운트 경로와 매칭되는 백엔드 다운로드 URL 설계
    # 프론트엔드가 백엔드 주소(예: localhost:8000) 뒤에 이 경로를 붙여 다운로드하게 만듬.
    download_path = f"/download/passport_pdfs/{file_name}"
    
    lines = raw_text.split("\n")
    refined_lines = [l.strip() for l in lines if l.strip() and not any(j in l for j in ["210m", "[백상지"])]
    clean_pdf_text = "\n".join(refined_lines)
    
    menu_path = pdf_doc.get("menu_path", [])
    full_hierarchy = " > ".join(menu_path) if menu_path else f"외교부 여권안내 > {title}"
        
    # LLM이 답변 마지막에 다운로드 버튼 문법을 출력할 수 있도록 컨텍스트에 힌트 삽입
    text_lines = [
        f"# {full_hierarchy}",
        clean_pdf_text,
        f"\nℹ️ 해당 서식 파일 다운로드 링크: [{file_name}]({download_path})" # 컨텍스트 하단에 주입
    ]
    full_chunk_text = "\n".join(text_lines)
    
    return {
        "title": full_hierarchy,
        "page_type": "passport_form_pdf",
        "text": full_chunk_text
    }