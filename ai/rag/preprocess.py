import json
import os

# [1] 전역 경로 설정 (실제 파일 위치에 맞게 세팅)
DATA_DIR = "data"
OUTPUT_JSONL = os.path.join(DATA_DIR, "processed", "saha_clean_chunks.jsonl")
OUTPUT_HTML = os.path.join(DATA_DIR, "processed", "saha_review_dashboard.html")

# ---------------------------------------------------------------------------
# [2] 각 크롤러 파일 별 함수 분리 및 전처리 로직
# ---------------------------------------------------------------------------

def process_general_docs(file_path):
    """
    1. 일반 웹페이지 (saha_docs.jsonl) 정밀 처리 함수
    - 서로 다른 doc_id(URL 다름)를 가졌더라도 본문 내용이 100% 일치하면 웹사이트 전역 중복으로 간주하고 필터링 합니다. 
    - 한 페이지 내에(url 동일)에서도 완전 일치하는 문단이 여러 개 있을 수 있는데, 이 경우에도 중복으로 간주하여 하나만 남기고 나머지는 버립니다.
    - 하이퍼링크를 텍스트에 포함된 경우, 마크다운 형식으로 [텍스트](URL) 치환합니다. 
    - 본문 내 표 데이터는 접근성용으로 중복해서 존재하는 경우가 많아서, 텍스트 내에 '|' 기호가 3개 이상 포함된 섹션은 표 데이터로 간주하여 자동으로 제거합니다.
    """
    chunks = []
    if not os.path.exists(file_path): 
        return chunks
        
    seen_texts = set()  # 전역 중복 차단기 (이미 한번 수집했던 본문텍스트를 저장해두는 집합 set)
        
    with open(file_path, "r", encoding="utf-8") as f:
        # <한 줄 씩 파일 읽기, 문서 기본 정보 추출>
        for line in f:
            if not line.strip(): continue # 빈 줄은 패스
            doc = json.loads(line.strip())
            doc_id = doc.get("doc_id")
            title = doc.get("title", "정보 안내")
            
            # 1.바로 가기 링크
            link_map = {}
            for link in doc.get("shortcut_links", []):
                link_text = link.get("text", "").strip()
                link_url = link.get("url", "").strip()
                if link_text and link_url:
                    link_map[link_text] = link_url

            # 2. 한 페이지 안에 들어있는 여러 section을 하나씩 검사
            for idx, sec in enumerate(doc.get("sections", [])):
                heading_path = sec.get("heading_path", [])
                block_type = sec.get("block_type", "")
                sec_text = sec.get("text", "").strip()
                
                # 기본 예외 처리
                # 전체 본문 백업 -> 중복 삭제
                # 글자수 15자 미만 -> 의미 없는 짧은 텍스트 제거
                # research_box -> 만족도 조사 박스 제거
                if block_type == "full_text_backup" or len(sec_text) < 15 or "research_box" in sec_text:
                    continue
                
                # 본문 내 표 중복 -> llm이 이해하기 쉬운 전자의 표 선택
                # 본문 내에 파이프(|) 기호가 3개 이상 등장 
                # -> 접근성용 중복 표 데이터로 판단하고 해당 섹션 전체를 제거 (표 데이터는 일반적으로 파이프 구분이 많음)
                if sec_text.count("|") >= 3:
                    continue
                
                # 텍스트 내의 보든 공백, 탭, 줄바꿈을 제거한 norm_text 생성 (예: 기초 생활 보장 -> 기초생활보장)
                # -> 띄어쓰기 or 엔터 개수가 달라서 중복 필터를 우회하는걸 방지하기 위함
                norm_text = "".join(sec_text.split())
                
                # 전역 차단기(seen_texts)에 등록된 본문은 중복이므로 스킵
                if norm_text in seen_texts:
                    continue
                
                # 부분 중복 및 포섭 관계 검사
                # 현재 문단이 이미 수집된 더 큰 문장 속에 포함되는 작은 문장일 경우 is_duplicate = True로 만들어서 탈락시킴
                is_duplicate = False
                for existing_norm in seen_texts:
                    if norm_text in existing_norm:
                        is_duplicate = True
                        break
                    
                # 필터링과 중복검사를 통과한 문단이므로 다음 문단을 검사할 때 비교 대상이 될 수 있도록 seen_texts에 추가 
                if is_duplicate:
                    continue
                
                seen_texts.add(norm_text)
                
                # 마크다운 변환 및 최종 청크 저장 
                # 본문 텍스트 내에 아까 저장해둔 링크 단어(text_key)가 나오면, 챗봇이 하이퍼링크를 줄 수 있도록 [단어](url) 형식으로 치환
                for text_key, url_val in link_map.items():
                    if text_key in sec_text and f"({url_val})" not in sec_text:
                        sec_text = sec_text.replace(text_key, f"[{text_key}]({url_val})")

                # '대메뉴 > 중메뉴 > 소메뉴' 형태로 제목을 구성
                # llm이 이해하기 쉽도록 제목 앞에는 #을 붙여서 마크다운 형식으로 만듦
                sub_title = " > ".join(heading_path) if heading_path else title
                refined_text = f"# {sub_title}\n\n{sec_text}"
                
                # *********나중에 date, view 등등 여러가지 추가 얘정
                # *********우선 중복 제거와 청킹, 표 정리를 우선으로 함 
                chunks.append({
                    "doc_id": f"{doc_id}_{idx}",
                    "url": doc.get("url"),
                    "title": sub_title,
                    "page_type": "일반안내(contents)",
                    "text": refined_text
                })
                
    return chunks




def process_civil_forms(file_path):
    """2. 민원안내 서식 (saha_civil_forms.jsonl) 처리 함수
    - 민원안내 데이터는 본문 내용이 길고 상세한 경우가 많아서, 청크 단위를 '민원 하나'로 잡아서 최대한 원문을 보존하는 방향으로 전처리 합니다."""
    chunks = []
    if not os.path.exists(file_path):
        return chunks
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): 
                continue
            
            form = json.loads(line.strip())
            
            if len(form.get("text", "")) < 80: 
                continue
                
            doc_id = form.get("doc_id")
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
            chunks.append({
                "doc_id": doc_id,
                "url": form.get("url"),
                "title": title,
                "page_type": "민원서식(civil_form)",
                "text": full_text
            })
            
    return chunks

#----------------------여기서부터 더 수정할 예정 

import json
import os

def process_bid_notices(file_path):
    """3. 입찰공고 (saha_bid_docs.jsonl) 처리 함수 (구조화 및 노이즈 제거 버전)"""
    chunks = []
    if not os.path.exists(file_path):
        return chunks
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): 
                continue
                
            bid = json.loads(line.strip())
            doc_id = bid.get("doc_id")
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
            chunks.append({
                "doc_id": doc_id, # 불필요한 접미사(_0)를 빼고 고유 ID 유지
                "url": bid.get("url"),
                "title": f"입찰정보 - {title}",
                "page_type": "입찰공고(bid_notice)",
                "text": refined_text
            })
            
    return chunks



def process_waste_guides(file_path):
    """4. 폐기물 안내 (saha_waste_docs.jsonl) 처리 함수"""
    chunks = []
    if not os.path.exists(file_path):
        return chunks
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            waste = json.loads(line.strip())
            doc_id = waste.get("doc_id")
            title = waste.get("title", "폐기물 안내")
            
            if doc_id == "431fe006b0edcf1d3ead855b8740c271":
                text_schedule = f"제목: {title} - 요일별 배출 지침\n\n[시간]\n배출: 저녁 7시~밤 10시 / 수거: 밤 10시~익일 오전 6시\n\n[요일별 종류]\n- 월: 플라스틱, 비닐, 의류\n- 화, 목, 일: 가연성 일반쓰레기, 음식물\n- 수: 투명페트병, 종이(박스), 유리병, 스티로폼, 캔, 불연성, 소형가전\n- 금, 토: ★배출 절대 금지★"
                text_price = f"제목: {title} - 봉투 및 용기 가격표\n\n[봉투 가격]\n5ℓ(220원), 10ℓ(430원), 20ℓ(850원), 30ℓ(1280원), 50ℓ(2070원), 75ℓ(3080원)\n[음식물칩 수수료]\n3ℓ(240원), 5ℓ(400원), 20ℓ(2000원)"
                
                chunks.append({"doc_id": f"{doc_id}_배출요일", "url": waste.get("url"), "title": f"{title} (배출요일)", "page_type": "환경청소(waste_guide)", "text": text_schedule})
                chunks.append({"doc_id": f"{doc_id}_가격표", "url": waste.get("url"), "title": f"{title} (가격표)", "page_type": "환경청소(waste_guide)", "text": text_price})
                
            elif doc_id == "cfdfcf50d9574c2e572eed62788e8c63":
                text_food = f"제목: {title} - 금지 품목 가이드\n\n[음식물 수거통에 넣으면 안되는 물질 (일반쓰레기 배출)]\n- 채소: 마늘대, 양파/마늘 껍질\n- 과일/견과: 복숭아 등 딱딱한 씨, 호두/밤/땅콩 껍질\n- 육류/어패류: 닭/돼지/소 뼈다귀, 조개/게/굴 껍데기"
                chunks.append({"doc_id": f"{doc_id}_0", "url": waste.get("url"), "title": title, "page_type": "환경청소(waste_guide)", "text": text_food})
    return chunks

# ---------------------------------------------------------------------------
# [3] 시각화 HTML 생성 전용 함수
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
        if "민원" in ptype: card_cls, badge_cls = "card civil", "badge civil"
        elif "입찰" in ptype: card_cls, badge_cls = "card bid", "badge bid"
        elif "환경" in ptype: card_cls, badge_cls = "card waste", "badge waste"
            
        html_content += f"""
                <div class="{card_cls}">
                    <div class="meta-row">
                        <span class="doc-id">ID: {chunk.get('doc_id')}</span>
                        <span class="{badge_cls}">{ptype}</span>
                    </div>
                    <div class="title">{chunk.get('title')}</div>
                    <a href="{chunk.get('url')}" target="_blank" style="font-size:13px; color:#3498db;">🔗 원본 구청 페이지</a>
                    <div class="content-box">{chunk.get('text').replace('<', '&lt;').replace('>', '&gt;')}</div>
                </div>
        """
    html_content += "</div></div></body></html>"
    
    # 디렉토리가 없으면 생성 후 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)

# ---------------------------------------------------------------------------
# [4] 메인 실행 컨트롤러 
# ---------------------------------------------------------------------------
def main():
    print("🚀 크롤링 데이터 전처리 및 시각화 빌드 가동...")
    all_chunks = []

    # 1) 각 파트별 전처리 함수를 호출하여 청크를 하나의 바구니에 수집
    # all_chunks.extend(process_general_docs(os.path.join(DATA_DIR, "raw", "saha_docs.jsonl")))
    # all_chunks.extend(process_civil_forms(os.path.join(DATA_DIR, "raw", "saha_civil_forms.jsonl")))
    all_chunks.extend(process_bid_notices(os.path.join(DATA_DIR, "raw", "saha_bid_docs.jsonl")))
    # all_chunks.extend(process_waste_guides(os.path.join(DATA_DIR, "raw", "saha_waste_docs.jsonl")))

    # 2) 파일 저장 처리 (JSONL)
    if not all_chunks:
        print("⚠️ 수집된 데이터 청크가 0개입니다. 소스 파일들의 경로('data/')나 위치를 다시 확인해주세요!")
        return

    os.makedirs(os.path.dirname(OUTPUT_JSONL), exist_ok=True)
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out_f:
        for chunk in all_chunks:
            out_f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
            
    print(f"✅ [1단계 완수] 통합 적재용 JSONL 완료 -> {OUTPUT_JSONL} ({len(all_chunks)}개 청크)")

    # 3) 대시보드 웹 페이지 생성 함수 호출
    generate_html_dashboard(all_chunks, OUTPUT_HTML)
    print(f"🖥️  [2단계 완수] 인간 검수용 대시보드 웹 뷰 완료 -> {OUTPUT_HTML}")
    print("✨ 모든 파이프라인이 성공적으로 완결되었습니다! ^-^")

if __name__ == "__main__":
    main()
    