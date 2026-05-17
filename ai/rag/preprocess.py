import os
import re
import json
from typing import List, Dict

# ==============================
# [1] 설정
# ==============================
INPUT_DIR = "data/raw"
OUTPUT_DIR = "data/processed"
OUTPUT_JSONL = os.path.join(OUTPUT_DIR, "saha_chunks.jsonl")

MIN_CHUNK_LEN = 50
MAX_CHUNK_LEN = 700
OVERLAP = 120

SECTION_HINTS = [
    "신청대상", "신청방법", "처리절차", "처리기간", "수수료",
    "구비서류", "제출서류", "유의사항", "문의처", "신고기한",
    "온라인 신청", "방문 신청"
]

MENU_SIGNALS = [
    "주메뉴", "사하구 홈페이지", "만족도 조사", "개인정보처리방침",
    "저작권", "공유", "프린트", "이전글", "다음글", "목록"
]
# [1] 제목이 될 수 없는 '내용 라벨' 정의 (띄어쓰기 무시하고 검사할 용도)
CONTENT_LABELS = ["구비서류", "수수료", "신청방법", "업무내용", "창구번호", "문의전화", "안내사항", "유의사항", "공통안내", "신청대상"]

# [2] 확실한 대분류 키워드 명시
MAJOR_KEYWORDS = ["일반·고충 민원", "어디서나 민원", "증명민원 통합발급", "편의시설", "가족관계등록 신고", "생활불편신고민원", "무인민원발급"]

# ==============================
# [2] 유틸리티 및 전처리
# ==============================
def ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def is_menu_like_chunk(text: str) -> bool:
    hit = sum(1 for x in MENU_SIGNALS if x in text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    short_lines = sum(1 for line in lines if len(line) <= 10)

    if hit >= 2:
        return True
    if lines and short_lines / len(lines) > 0.65:
        return True
    return False


# ==============================
# [3] chunk 분리 및 조립 로직(서식 별 함수 분리)
# ==============================

def is_likely_major(line, lines, idx):
    """
    해당 줄이 대분류(Major)일 가능성을 점수로 계산합니다.
    """
    score = 0
    
    # 1. 길이 조건: 대분류는 보통 짧고 명료합니다 (20자 미만)
    if len(line) < 20: score += 2
    
    # 2. 제외 조건: 데이터성 기호가 있으면 제목이 아님
    if any(k in line for k in [":", "：", "http", "www", "→"]): return False
    
    # 3. 위치 조건: 대분류는 보통 섹션의 처음에 나옵니다.
    # 바로 다음 줄(idx+1)에 '창구', '전화', '내용' 등의 데이터가 붙는다면 이건 100% 대분류입니다.
    if idx + 1 < len(lines):
        next_line = lines[idx+1]
        if any(k in next_line for k in ["창구", "전화", "문의", "업무", "내용"]):
            score += 5

    # 4. 키워드 조건 (범용): '민원', '안내', '시설', '현황', '방법' 등으로 끝나는 경우
    if line.endswith(("민원", "안내", "현황", "방법", "시설", "신고", "발급", "센터")):
        score += 3

    return score >= 5 # 5점 이상이면 대분류로 확정

def make_chunks_automated(doc: Dict) -> List[Dict]:
    content = doc.get("text", "")
    # ... (본문 추출 생략) ...
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    
    results = []
    current_major = "일반" # 기본값
    current_minor = ""
    major_common_info = []
    chunk_buffer = []

    for i, line in enumerate(lines):
        # [자동화 핵심] 대분류 감지
        if is_likely_major(line, lines, i):
            if chunk_buffer:
                save_chunk(results, doc, current_major, current_minor, major_common_info, chunk_buffer)
                chunk_buffer = []
            
            # 만약 현재 줄이 '통합발급' 같은 큰 단위를 포함하면 Major로 격상
            current_major = line
            current_minor = ""
            major_common_info = []
            continue

        # [자동화 핵심] 중분류 감지 
        # (이미 대분류가 잡힌 상태에서, 데이터는 아닌데 짧은 줄이 나오면 중분류)
        elif len(line) < 25 and ":" not in line and not any(k in line for k in ["창구", "전화"]):
            if chunk_buffer:
                save_chunk(results, doc, current_major, current_minor, major_common_info, chunk_buffer)
                chunk_buffer = []
            current_minor = line
            continue

        # 데이터 적재 (창구번호 등은 공통 정보로 빼기)
        if any(k in line for k in ["창구", "전화", "문의"]) and not current_minor:
            major_common_info.append(line)
        else:
            chunk_buffer.append(line)

    # 마지막 버퍼 처리
    if chunk_buffer:
        save_chunk(results, doc, current_major, current_minor, major_common_info, chunk_buffer)

    return results

def build_chunk_text(doc, section_text: str, current_context: str) -> str:
    page_title = doc.get("title", "")
    menu_path = " > ".join(doc.get("menu_path", []))
    
    header = f"### [분류: {menu_path}] ###\n"
    header += f"### [정보원: {page_title}"
    if current_context and current_context != page_title:
        header += f" - {current_context}"
    header += " ] ###"

    formatted_text = f"{header}\n\n[상세 내용]\n{section_text}"
    return clean_text(formatted_text)

def save_chunk(results, doc, major, minor, common_info, buffer):
    if not buffer: return

    page_title = doc.get("title", "안내")
    source_context = f"{page_title} - {major}"
    if minor:
        source_context += f" - {minor}"
    
    content_parts = []
    if common_info:
        content_parts.append("[공통 안내]\n" + "\n".join(common_info))
    content_parts.append("[상세 내용]\n" + "\n".join(buffer))
    
    full_text = f"### [분류: {'>'.join(doc.get('menu_path', []))}] ###\n" \
                f"### [정보원: {source_context} ] ###\n\n" \
                + "\n\n".join(content_parts)

    results.append({
        "chunk_id": f"{doc['doc_id']}_{len(results)}",
        "doc_id": doc["doc_id"],
        "url": doc.get("url", ""),
        "title": page_title,
        "menu_path": doc.get("menu_path", []),
        "chunk_text": full_text,
        "metadata": {
            "major": major,
            "minor": minor,
            "context": source_context
        },
        "source": "saha.go.kr"
    })
    
def is_likely_heading(line, lines, idx):
    # [방어 로직] 1. 제목이 20자 넘어가면 일단 의심 (보통 제목은 짧음)
    if not (2 <= len(line) <= 25): return False, False
    
    # [방어 로직] 2. 숫자로 시작하거나 "※", "①" 같은 기호는 99% 내용임
    if re.match(r"^[0-9※①②③④⑤\-\s]", line): return False, False

    # [방어 로직] 3. 문장 중간에 조사가 많으면 내용임 (잘린 문장 방지)
    if any(k in line for k in ["는 ", "를 ", "은 ", "의 ", "에 "]): return False, False

    # [방어 로직] 4. 데이터성 구분자 확인
    if ":" in line or "：" in line or "→" in line: return False, False

    # --- 여기서부터는 분류 판단 ---
    is_major = False
    next_line = lines[idx+1] if idx + 1 < len(lines) else ""
    
    # 강력한 대분류 신호: 다음 줄에 핵심 속성이 붙어있는 경우
    # 예: 일반·고충 민원 (현재줄) -> 업무내용 (다음줄)
    if any(k in next_line for k in ["업무내용", "창구번호", "문의전화", "구비서류"]):
        is_major = True
    
    # 키워드 엔딩 (민원, 안내, 센터 등)
    if line.endswith(("민원", "안내", "신고", "시설", "센터")):
        is_major = True

    return True, is_major

def make_chunks_universal(doc):
    raw_text = doc.get("text", "")
    # [본문] 영역 추출
    body_part = raw_text.split("[본문]")[1].split("[구조정보]")[0].strip() if "[본문]" in raw_text else raw_text
    lines = [line.strip() for line in body_part.splitlines() if line.strip()]
    
    # UI 노이즈 제거
    lines = [l for l in lines if l not in ["Home", "열기", "닫기", "인쇄하기", "전자민원"]]
    
    results = []
    curr_major = doc.get("title", "일반 안내") # 페이지 제목을 기본 대분류로
    curr_minor = ""
    common_info = [] # 창구번호 등 섹션 공통 정보
    buffer = []
    
    for i, line in enumerate(lines):
        is_heading, is_major = is_likely_heading(line, lines, i)
        
        if is_heading:
            if buffer:
                save_chunk(results, doc, curr_major, curr_minor, common_info, buffer)
                buffer = []
            
            if is_major:
                curr_major = line
                curr_minor = ""
                common_info = [] # 대분류가 바뀌면 공통정보 초기화
            else:
                curr_minor = line
            continue

        # [수정] 속성 정보(창구/전화)를 무조건 common_info로 빼지 말고,
        # '내용(buffer)'에도 포함시켜야 문맥이 끊기지 않습니다.
        if any(k in line for k in ["창구번호", "문의전화", "업무내용", "수수료"]):
            common_info.append(line)
        
        buffer.append(line) # 무조건 본문에도 넣어서 AI가 읽게 함

    # 마지막 남은 덩어리 저장
    if buffer:
        save_chunk(results, doc, curr_major, curr_minor, common_info, buffer)

    return results
# [3] chunk 분리 로직 (논리 구조 중심)
def make_chunks_format_docs(doc): #사하구청 전체 크롤러
    raw_text = doc.get("text", "")
    content = raw_text.split("[본문]")[1].split("[구조정보]")[0].strip() if "[본문]" in raw_text else raw_text
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    
    results = []
    curr_major = "안내 개요" # [수정] 인트로 텍스트가 날아가지 않도록 초기 방 이름 설정
    curr_minor = ""
    common_info = []
    buffer = []

    for i, line in enumerate(lines):
        # 띄어쓰기를 없앤 클린 버전으로 내용 라벨 검사 ('수 수 료' 완벽 방어)
        clean_line = line.replace(" ", "")
        
        # [Step 1] 제목 판별 로직 (더욱 정교하게)
        is_content_label = any(label in clean_line for label in CONTENT_LABELS) and len(clean_line) < 15
        # '번째'를 추가하여 "메뉴 첫번째" 같은 문장이 제목으로 잘리는 것 방지
        ends_with_verb = line.endswith(("다.", "다", "요.", "요", "니다", "습니다", "바랍니다", "번째"))
        has_colon = any(c in line for c in [":", "：", "→"])
        is_long = len(line) > 25
        
        # 대분류 키워드가 포함되어 있으면 무조건 제목으로 인정
        is_major_explicit = any(k in line for k in MAJOR_KEYWORDS)

        if is_major_explicit:
            is_heading = True
        elif is_long or has_colon or ends_with_verb or is_content_label:
            is_heading = False
        else:
            is_heading = True

        if is_heading:
            if buffer:
                save_chunk(results, doc, curr_major, curr_minor, common_info, buffer)
                buffer = []

            # [Step 2] 대분류 vs 중분류 판별
            is_new_major = is_major_explicit
            # 키워드가 없더라도, 발급/안내 등으로 끝나면서 다음 줄에 창구가 나오면 대분류
            if not is_new_major and line.endswith(("민원", "시설", "안내", "신고", "발급")) and i + 1 < len(lines):
                if any(k in lines[i+1] for k in ["창구", "전화", "문의", "업무"]):
                    is_new_major = True

            if is_new_major:
                curr_major = line
                curr_minor = ""
                common_info = [] 
            else:
                curr_minor = line
            continue

        # [Step 3] 데이터 적재
        if not curr_minor and any(k in line for k in ["창구", "전화", "문의", "업무내용"]):
            common_info.append(line)
        else:
            buffer.append(line)

    if buffer:
        save_chunk(results, doc, curr_major, curr_minor, common_info, buffer)

    return results

def make_chunks_format_forms(doc: Dict) -> List[Dict]: #민원 양식 전처리
    results = []
    
    # 1. 딕셔너리에서 풍부한 속성값들을 안전하게 추출합니다.
    title = doc.get("title", "민원 안내")
    category = doc.get("category", "일반")
    department = doc.get("department", "미지정")
    phone = doc.get("phone", "비공개")
    processing_period = doc.get("processing_period", "즉시")
    required_documents = doc.get("required_documents", "없음")
    submission_place = doc.get("submission_place", "행정복지센터")
    fee = doc.get("fee", "없음")
    notes = doc.get("notes", "")
    review_criteria = doc.get("review_criteria", "")
    workflow = doc.get("workflow", "")
    
    # 2. 고우니(AI)가 읽었을 때 한눈에 정보를 파악할 수 있도록 RAG 맞춤형 서식으로 재조립합니다.
    full_text = f"### [민원명: {title}] ###\n"
    full_text += f"- 분류/분야: {category}\n"
    full_text += f"- 담당부서 및 문의처: {department} (☎ {phone})\n"
    full_text += f"- 처리기간: {processing_period}\n"
    full_text += f"- 신청 및 제출처: {submission_place}\n"
    full_text += f"- 수수료 및 기타비용: {fee}\n\n"
    
    full_text += f"[구비 서류]\n{required_documents}\n\n"
    
    if review_criteria:
        full_text += f"[행정기관 심사 기준]\n{review_criteria}\n\n"
    if workflow:
        full_text += f"[업무 처리 흐름도]\n{workflow}\n\n"
    if notes:
        full_text += f"[유의 사항]\n{notes}\n\n"
        
    # 3. 기존의 save_chunk와 구조적 호환성을 맞추어 청크 리스트에 적재합니다.
    results.append({
        "chunk_id": f"{doc['doc_id']}_0", # 이 데이터는 문서 1개가 하나의 완벽한 덩어리이므로 _0 고정
        "doc_id": doc["doc_id"],
        "url": doc.get("url", ""),
        "title": title,
        "menu_path": [category, title],
        "chunk_text": clean_text(full_text), # 텍스트 공백 정제
        "metadata": {
            "major": category,
            "minor": title,
            "context": f"{title} 안내"
        },
        "source": "saha.go.kr"
    })
    
    return results
    return results
# ==============================
# [4] 실행
# ==============================
def preprocess():
    ensure_dir(OUTPUT_DIR)
    total_docs = 0
    total_chunks = 0
    #출력파일은 하나
    with open(OUTPUT_JSONL, "w", encoding="utf-8") as fout:
        #raw 폴더 안의 모든 파일을 가져옴
        for file_name in os.listdir(INPUT_DIR):
            file_path = os.path.join(INPUT_DIR, file_name)
            
            # 맥 디렉토리 숨김파일(.DS_Store 등) 예외 처리
            if file_name.startswith('.'): 
                continue
                
            print(f"📦 현재 처리 중인 파일: {file_name}")
            
            # 각 파일 내부를 열어서 한 줄씩 파싱
            with open(file_path, "r", encoding="utf-8") as fin:
                for line in fin:
                    line = line.strip()
                    if not line: 
                        continue
                        
                    doc = json.loads(line)
                    total_docs += 1
                    
                    # ⭐ [핵심 분기 처리] 파일 구조(컬럼)를 보고 처리 함수를 동적으로 지정합니다.
                    if "page_type" in doc:
                        # 새로 추가된 예쁜 JSON 형태의 데이터라면 -> 서식 B로 작동!
                        chunks = make_chunks_format_forms(doc)
                    else:
                        # 예전의 통짜 text 위주의 데이터라면 -> 기존의 쪼개기(서식 A)로 작동!
                        chunks = make_chunks_format_docs(doc)
                        
                    total_chunks += len(chunks)
                    
                    # 어떤 서식을 거쳤든 공통된 규격으로 출력 파일에 차곡차곡 기록!
                    for chunk in chunks:
                        fout.write(json.dumps(chunk, ensure_ascii=False) + "\n")

    print("\n✨ 모든 크롤링 파일 통합 전처리 완료! ✨")
    print(f"- 총 처리한 원본 문서 수: {total_docs}")
    print(f"- 최종 생성된 RAG Chunk 수: {total_chunks}")
    print(f"- 통합 저장 완료된 파일 주소: {OUTPUT_JSONL}")

if __name__ == "__main__":
    preprocess()