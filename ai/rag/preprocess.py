import os
import json
import re

def clean_web_page_data(data):
    shortcuts = data.get("shortcut_links", []) or []
    sections = data.get("sections", []) or []
    shortcuts_sorted = sorted(shortcuts, key=lambda x: len(x.get('text', '')), reverse=True)
    
    seen_texts = set()
    rebuilt_chunks = []
    full_text_snapshot = ""
    
    for section in sections:
        text_content = section.get("text", "")
        if not text_content: 
            continue
        text_content = text_content.strip()
        
        if text_content in full_text_snapshot:
            continue
            
        for link_obj in shortcuts_sorted:
            keyword = link_obj.get("text")
            url = link_obj.get("raw_href") or link_obj.get("url")
            if keyword and url and keyword in text_content:
                if f"[{keyword}]" not in text_content:
                    text_content = text_content.replace(keyword, f"[{keyword}]({url})")
        
        if text_content in full_text_snapshot:
            continue
            
        path_list = section.get("heading_path", [])
        path_str = " > ".join(path_list) if path_list else "일반 안내"
        
        # [보정 가드]: 기형적 콤마 오타 사전 교정
        text_content = re.sub(r'1,23,0834', '1,230,834', text_content)
        text_content = re.sub(r'1,230834', '1,230,834', text_content)
        
        chunk = f"[{path_str}]\n{text_content}"
        rebuilt_chunks.append(chunk)
        full_text_snapshot += "\n" + text_content

    # 💡 [안전한 범용 표 추출 및 텍스트 청정 파이프라인]
    lines = "\n".join(rebuilt_chunks).split('\n')
    pure_contents = []
    current_table_rows = []
    
    for line in lines:
        if line.count('|') >= 2:
            current_table_rows.append(line.strip())
        else:
            if current_table_rows:
                pure_contents.append(parse_generic_table(current_table_rows))
                current_table_rows = []
            pure_contents.append(line)
            
    if current_table_rows:
        pure_contents.append(parse_generic_table(current_table_rows))

    # 💡 [안전한 라인 필터링]: 수만 개 문서의 본문 유실을 방지하기 위해
    # 임의로 매칭해서 지우지 않고, 명백하게 깨진 '단독 파편 줄'만 타겟 청소
    cleaned_final_lines = []
    for line in pure_contents:
        stripped_line = line.strip()
        
        # 마크다운 표 구조는 무조건 보존
        if "|" in line:
            cleaned_final_lines.append(line)
            continue
            
        # 1. 금액이나 숫자만 덜렁 한 줄로 남은 노이즈 행 제거 (ex: "820,556", "2,564,238")
        if re.match(r'^[\d,]+$', stripped_line):
            continue
            
        # 2. 가구원 수 규격에서 단순 열 이름만 덜렁 쪼개져 있는 유령 줄 제거
        if stripped_line in ["1인", "2인", "3인", "4인", "5인", "6인", "가구원 수"]:
            continue
            
        # 3. 급여명 찌꺼기 중 텍스트 파편으로 단독 격리된 짧은 줄만 스킵 (설명 문장 내부 단어는 안전)
        if stripped_line in ["(중위 32%)", "(중위 40%)", "(중위 48%)", "(중위 50%)"]:
            continue
            
        cleaned_final_lines.append(line)

    data["text"] = f"제목: {data.get('title', '정보')}\n" + "\n".join(cleaned_final_lines).strip()
    data["sections"] = sections
    return data


def parse_generic_table(table_rows):
    """
    어떤 형태의 크롤링 표가 들어와도 중복된 컬럼명 행을 완벽하게 걸러내고
    순수 데이터만 마크다운 표로 변환하는 최종 고도화 파서
    """
    if not table_rows:
        return ""
        
    md_table = []
    headers = []
    valid_rows = []
    
    for row in table_rows:
        # 공백 제거하여 조각내기
        parts = [p.strip() for p in row.split('|') if p.strip()]
        if not parts:
            continue
            
        # 💡 [정밀 중복 가드]: 헤더 정보와 데이터가 100% 겹치는 노이즈 행 차단
        # 예: "| 가구원 수 | 1인: 1인 | 2인: 2인 |" 처럼 Key와 Value가 완전히 똑같은 
        # 데이터 조각들("1인: 1인")이 발견되면 데이터가 아닌 '껍데기 행'이므로 과감히 스킵합니다.
        is_duplicate_header = False
        for p in parts[1:]:
            if ":" in p:
                k, v = p.split(':', 1)
                if k.strip() == v.strip():  # "1인" == "1인" 처럼 겹치는 경우
                    is_duplicate_header = True
                    break
        
        if is_duplicate_header:
            continue
            
        # 데이터 유효성 검사 (콜론 기호가 들어간 실재 데이터 행만 수집)
        if any(":" in p for p in parts[1:]):
            valid_rows.append(parts)
            
    if not valid_rows:
        return ""
        
    # 동적 마크다운 헤더 뼈대 생성
    headers.append("구분")
    for part in valid_rows[0][1:]:
        if ":" in part:
            h_name = part.split(':')[0].strip()
            if h_name not in headers:
                headers.append(h_name)
                
    md_table.append("| " + " | ".join(headers) + " |")
    md_table.append("| " + " | ".join([":---" if i == 0 else ":---:" for i in range(len(headers))]) + " |")
    
    # 데이터 매핑 및 오타 보정 최종 바인딩
    for parts in valid_rows:
        row_title = parts[0].strip()
        if ":" in row_title:
            row_title = row_title.split(':')[-1].strip()
            
        if row_title.startswith('[') and row_title.endswith(']'):
            continue
            
        row_cells = [row_title]
        for part in parts[1:]:
            if ":" in part:
                val = part.split(':')[1].strip()
                # 마지막까지 기형적 콤마 오타 패턴 감시 보정
                if "1,23,0834" in val or "1,230834" in val:
                    val = "1,230,834"
                row_cells.append(val)
                
        if len(row_cells) == len(headers):
            md_table.append("| " + " | ".join(row_cells) + " |")
            
    return "\n" + "\n".join(md_table) + "\n"

# 3. 💡 [안전하게 버그 수정] 온전한 JSON 파싱 함수
def parse_safe_jsonl_line(line):
    line_stripped = line.strip()
    if not line_stripped:
        return None
        
    # 주소의 http:// 나 https:// 를 해치지 않고, 
    # 오직 라인 맨 앞이 '//' 로 시작하는 순수 주석 라인만 스킵
    if line_stripped.startswith("//"):
        return None
        
    try:
        return json.loads(line_stripped)
    except Exception as e:
        # 파싱 실패할 경우 혹시 모를 꼬인 문자열 추적을 위해 에러 찍기
        print(f"   ⚠️ 파싱 에러 디버그 로그: {str(e)}")
        return None

# 🚀 4. 메인 파이프라인 처리부
def main():
    # 1. 현재 스크립트 파일의 절대 경로 기준 설정
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, "..", ".."))
    
    # 2. 프로젝트 루트 기준으로 입력(raw) 및 출력(processed) 폴더 매핑
    input_folder = os.path.join(project_root, "data", "raw")
    output_folder = os.path.join(project_root, "data", "processed")
    output_file_path = os.path.join(output_folder, "saha_clean_docs.json")
    
    # 출력 폴더가 없으면 자동 생성
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
        
    unified_database = []

    print(f"🔍 입력 폴더 스캔 시작: {input_folder}")
    
    if not os.path.exists(input_folder):
        print(f"❌ 에러: [{input_folder}] 경로가 존재하지 않습니다. 폴더 위치를 확인해 주세요.")
        return

    # 3. 폴더 안의 모든 파일 순회
    for filename in os.listdir(input_folder):
        file_path = os.path.join(input_folder, filename)
        
        # 💡 [JSONL 파일 처리 분기]
        if filename.lower().endswith('.jsonl'):
            print(f"📦 JSONL 파일 정제 중: {filename}")
            with open(file_path, "r", encoding="utf-8") as f:
                for line_num, line in enumerate(f, 1):
                    page_data = parse_safe_jsonl_line(line)
                    if not page_data: 
                        continue
                    
                    # ⭐ [노이즈 필터링]: 알맹이 없는 바로가기 데이터(menu_shortcut)는 과감히 제외
                    if page_data.get("page_type") == "menu_shortcut":
                        continue
                        
                    # 데이터 구조에 따른 정제 함수 호출
                    if "sections" in page_data and page_data["sections"]:
                        processed_page = clean_web_page_data(page_data)
                    else:
                        processed_page = clean_pdf_extracted_data(page_data)
                        
                    # 최종 마스터 스키마 규격에 맞춰 압축
                    minimal_data = {
                        "doc_id": processed_page.get("doc_id"),
                        "url": processed_page.get("url"),
                        "title": processed_page.get("title", "정보 없음"),
                        "page_type": processed_page.get("page_type", "contents"),
                        "text": processed_page.get("text")
                    }
                    
                    if minimal_data["text"]:
                        unified_database.append(minimal_data)
            
        # 💡 [일반 단일 JSON 파일 처리 분기]
        elif filename.lower().endswith('.json'):
            print(f"🌐 단일 JSON 파일 정제 중: {filename}")
            with open(file_path, "r", encoding="utf-8") as f:
                try:
                    page_data = json.load(f)
                    
                    # ⭐ [노이즈 필터링]: 일반 JSON 파일에서도 menu_shortcut 타입은 스킵
                    if page_data.get("page_type") == "menu_shortcut":
                        continue
                        
                    if "sections" in page_data and page_data["sections"]:
                        processed_page = clean_web_page_data(page_data)
                    else:
                        processed_page = clean_pdf_extracted_data(page_data)
                        
                    minimal_data = {
                        "doc_id": processed_page.get("doc_id"),
                        "url": processed_page.get("url"),
                        "title": processed_page.get("title", "정보 없음"),
                        "page_type": processed_page.get("page_type", "contents"),
                        "text": processed_page.get("text")
                    }
                    
                    if minimal_data["text"]:
                        unified_database.append(minimal_data)
                except Exception as e:
                    print(f"❌ 단일 JSON 파싱 에러 스킵: {filename} - {str(e)}")
                    continue

    # 4. processed 폴더 안에 가벼워진 단 하나의 JSON 마스터셋 파일로 저장
    with open(output_file_path, "w", encoding="utf-8") as f:
        json.dump(unified_database, f, ensure_ascii=False, indent=2)
        
    print("\n" + "="*40)
    print(f"🎉 전처리 파이프라인 완전 빌드 완료!")
    print(f"📦 총 {len(unified_database)}개의 핵심 문서가 노이즈 없이 통합되었습니다.")
    print(f"💾 최종 저장 경로: {output_file_path}")
    
    # ... (기존 json.dump 코드 바로 아래에 이어서 작성) ...

    # 💡 [QA 검토용 HTML 자동 생성 가드]
    html_file_path = os.path.join(output_folder, "qa_viewer.html")
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>사하구청 RAG 데이터 전처리 QA 검토 뷰어</title>
        <style>
            body { font-family: 'Malgun Gothic', sans-serif; background: #f5f6f7; padding: 30px; color: #333; }
            .container { max-width: 1100px; margin: 0 auto; }
            h1 { text-align: center; color: #1e293b; margin-bottom: 30px; }
            .doc-card { background: white; padding: 25px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); margin-bottom: 25px; border-left: 6px solid #3b82f6; }
            .meta { font-size: 0.9em; color: #64748b; margin-bottom: 15px; padding-bottom: 10px; border-bottom: 1px dashed #e2e8f0; }
            .meta span { margin-right: 15px; font-weight: bold; }
            .title { font-size: 1.3em; color: #0f172a; font-weight: bold; margin-bottom: 10px; }
            .text-box { background: #f8fafc; padding: 20px; border-radius: 8px; border: 1px solid #e2e8f0; white-space: pre-wrap; font-size: 0.95em; line-height: 1.6; }
            table { border-collapse: collapse; width: 100%; margin-top: 15px; background: white; }
            th, td { border: 1px solid #cbd5e1; padding: 10px; text-align: center; font-size: 0.9em; }
            th { background: #f1f5f9; font-weight: bold; color: #1e293b; }
            a { color: #2563eb; text-decoration: none; }
            a:hover { text-decoration: underline; }
        </style>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    </head>
    <body>
        <div class="container">
            <h1>🔍 사하구청 데이터 전처리 마스터셋 QA 뷰어</h1>
    """
    
    # 생성된 데이터 중 상위 몇 개 또는 전체를 HTML 카드로 변환 (검토용으로 50개만 보거나 전체 보거나 조절 가능)
    # 여기서는 편의상 수집된 모든 문서를 순회합니다.
    for doc in unified_database:
        html_content += f"""
            <div class="doc-card">
                <div class="title">📄 {doc['title']}</div>
                <div class="meta">
                    <span>ID:</span> {doc['doc_id']} | 
                    <span>유형:</span> {doc['page_type']} | 
                    <span>출처 URL:</span> <a href="{doc['url']}" target="_blank">{doc['url']}</a>
                </div>
                <div class="text-box" id="content-{doc['doc_id']}"></div>
                <script>
                    // 마크다운 문법([링크], |표|)을 HTML 태그로 이쁘게 렌더링해주는 마법의 한 줄
                    document.getElementById("content-{doc['doc_id']}").innerHTML = marked.parse(`{doc['text']}`);
                </script>
            </div>
        """
        
    html_content += """
        </div>
    </body>
    </html>
    """
    
    with open(html_file_path, "w", encoding="utf-8") as h_f:
        h_f.write(html_content)
        
    print(f"🖥️  검토용 웹뷰어 페이지가 생성되었습니다: {html_file_path}")
    print("="*40)
    
if __name__ == "__main__":
    main()