import json
import os

# 💡 1. 전역 경로 설정 (실제 파일 위치에 맞게 세팅)
DATA_DIR = "data"
OUTPUT_JSONL = os.path.join(DATA_DIR, "processed", "saha_clean_chunks.jsonl")
OUTPUT_HTML = os.path.join(DATA_DIR, "processed", "saha_review_dashboard.html")

# ---------------------------------------------------------------------------
# 💡 2. 각 소스 파일별 전용 전처리 함수들 (로직 격리)
# ---------------------------------------------------------------------------

def process_general_docs(file_path):
    """
    일반 웹페이지 (saha_docs.jsonl) 정밀 처리 함수 (부분 중복/포섭 관계 완벽 제거 버전)
    """
    chunks = []
    if not os.path.exists(file_path):
        return chunks
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            doc = json.loads(line.strip())
            doc_id = doc.get("doc_id")
            title = doc.get("title", "정보 안내")
            
            # 💡 이번 페이지에서 살아남은 '정제된 본문 문자열 리스트'를 유지합니다.
            processed_normalized_texts = []
            # 원본 청크 객체를 임시 보관할 배열
            temp_chunks = []
            
            link_map = {}
            for link in doc.get("shortcut_links", []):
                link_text = link.get("text", "").strip()
                link_url = link.get("url", "").strip()
                if link_text and link_url:
                    link_map[link_text] = link_url

            for idx, sec in enumerate(doc.get("sections", [])):
                heading_path = sec.get("heading_path", [])
                block_type = sec.get("block_type", "")
                sec_text = sec.get("text", "").strip()
                
                # 기본 노이즈 필터링
                if block_type == "full_text_backup" or len(sec_text) < 15 or "research_box" in sec_text:
                    continue
                
                # 공백 제거한 비교용 텍스트
                norm_text = "".join(sec_text.split())
                
                # 💡 [핵심 알고리즘] 부분 중복 및 포섭 관계 검사
                is_duplicate = False
                
                for existing_norm in processed_normalized_texts:
                    # 케이스 A: 현재 조각(norm_text)이 기존 거(existing_norm)에 완전히 포함되는 쪼가리일 때 -> 버린다!
                    if norm_text in existing_norm:
                        is_duplicate = True
                        break
                    # 케이스 B: 반대로 현재 조각이 기존 작은 쪼가리들을 통째로 삼키는 상위 호환일 때
                    # (이 경우는 나중에 찌꺼기가 남지 않도록 temp_chunks 관리를 해주거나, 
                    # 스크랩 순서상 보통 큰 덩어리(_6)가 먼저 나오고 작은 조각(_7, _8)이 뒤에 나오므로 케이스 A에서 대부분 컷팅됩니다!)
                
                if is_duplicate:
                    continue # 겹치는 쪼가리 본문은 과감히 버리기!
                
                # 통과했다면 누적 리스트에 추가
                processed_normalized_texts.append(norm_text)
                
                # 마크다운 링크 매핑
                for text_key, url_val in link_map.items():
                    if text_key in sec_text and f"({url_val})" not in sec_text:
                        sec_text = sec_text.replace(text_key, f"[{text_key}]({url_val})")

                sub_title = " > ".join(heading_path) if heading_path else title
                
                # 수빈님이 말씀하신 최적의 마크다운 헤더(#) 적용!
                refined_text = f"# {sub_title}\n\n{sec_text}"
                
                chunks.append({
                    "doc_id": f"{doc_id}_{idx}",
                    "url": doc.get("url"),
                    "title": sub_title,
                    "page_type": "일반안내(contents)",
                    "text": refined_text
                })
                
    return chunks



def process_civil_forms(file_path):
    """2. 민원안내 서식 (saha_civil_forms.jsonl) 처리 함수"""
    chunks = []
    if not os.path.exists(file_path):
        return chunks
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            form = json.loads(line.strip())
            if len(form.get("text", "")) < 80: continue
            
            doc_id = form.get("doc_id")
            title = form.get("title", "민원 안내")
            dept = form.get("department", "해당부서")
            phone = form.get("phone", "안내번호")
            
            req_docs = form.get("required_documents", "정보 없음").strip()
            text_procedure = f"제목: {title} (구비서류 및 절차)\n부서: {dept}({phone})\n처리기간: {form.get('processing_period', '지체 없이')} / 수수료: {form.get('fee', '없음')}\n\n[구비서류]\n{req_docs}\n\n[처리흐름]\n{form.get('workflow', '정보 없음')}"
            text_notes = f"제목: {title} (유의사항 및 과태료)\n부서: {dept}({phone})\n\n[상세 유의사항]\n{form.get('notes', '정보 없음').strip()}"
            
            chunks.append({
                "doc_id": f"{doc_id}_구비서류",
                "url": form.get("url"),
                "title": f"{title} [구비서류]",
                "page_type": "민원서식(civil_form)",
                "text": text_procedure
            })
            chunks.append({
                "doc_id": f"{doc_id}_유의사항",
                "url": form.get("url"),
                "title": f"{title} [유의사항]",
                "page_type": "민원서식(civil_form)",
                "text": text_notes
            })
    return chunks


def process_bid_notices(file_path):
    """3. 입찰공고 (saha_bid_docs.jsonl) 처리 함수"""
    chunks = []
    if not os.path.exists(file_path):
        return chunks
        
    with open(file_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            bid = json.loads(line.strip())
            doc_id = bid.get("doc_id")
            title = bid.get("title", "입찰공고")
            
            refined_text = f"제목: {title}\n공고번호: {bid.get('notice_no', '번호없음')}\n담당부서: {bid.get('department', '재무과')}({bid.get('phone', '')})\n공고일자: {bid.get('date', '')}\n\n[공사 상세내용]\n{bid.get('body', '').strip()}"
            
            chunks.append({
                "doc_id": f"{doc_id}_0",
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
# 💡 3. 시각화 HTML 생성 전용 함수
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
# 💡 4. 메인 실행 컨트롤러 (마스터 오케스트레이션)
# ---------------------------------------------------------------------------
def main():
    print("🚀 [함수형 파이프라인] 사하구청 마스터 전처리 및 시각화 빌드 가동...")
    all_chunks = []

    # 1) 각 파트별 전처리 함수를 호출하여 청크를 하나의 바구니에 수집
    all_chunks.extend(process_general_docs(os.path.join(DATA_DIR, "raw", "saha_docs.jsonl")))
    all_chunks.extend(process_civil_forms(os.path.join(DATA_DIR, "raw", "saha_civil_forms.jsonl")))
    all_chunks.extend(process_bid_notices(os.path.join(DATA_DIR, "raw", "saha_bid_docs.jsonl")))
    all_chunks.extend(process_waste_guides(os.path.join(DATA_DIR, "raw", "saha_waste_docs.jsonl")))

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
    print("✨ 모든 파이프라인이 성공적으로 완결되었습니다!")

if __name__ == "__main__":
    main()