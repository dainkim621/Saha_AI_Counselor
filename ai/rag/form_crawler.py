import os
import re
import json
import time
import hashlib
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

LIST_URL = "https://www.saha.go.kr/portal/civil/list.do?mId=0103080100"
OUTPUT_DIR = "data/raw"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "saha_civil_forms.jsonl")

RECENT_YEAR_LIMIT = 5   # 최근 몇년간 자료를 검색할건지
CURRENT_YEAR = 2026
MIN_YEAR = CURRENT_YEAR - RECENT_YEAR_LIMIT

MAX_LIST_PAGES = 30       # 안씀
REQUEST_DELAY = 0.5
TIMEOUT = 15

HEADERS = {"User-Agent": "Mozilla/5.0"}

FIELD_NAMES = [
    "민원분야",
    "담당부서",
    "담당자 전화번호",
    "처리기간",
    "신청서 및 구비서류",
    "제출처",
    "수수료 및 기타비용",
    "유의사항",
    "행정기관의 심사기준",
    "업무처리 흐름도",
    "이의신청",
    "기타",
]
# 우선순위 : 1. 전입·이사 2. 증명서 발급 3. 복지·지원금
TARGET_KEYWORDS = [
    "전입", "이사", "주민등록",
    "등본", "초본", "인감", "증명",
    "복지", "지원금", "수급", "장애", "출산", "보육"
]


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def make_id(url):
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def get_list_url(page):
    if page == 1:
        return LIST_URL

    return f"{LIST_URL}&page={page}"


def fetch(session, url):
    response = session.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    return response.text


def extract_view_links_from_list(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        full_url = urljoin(base_url, href)
        full_url, _ = urldefrag(full_url)

        if "/portal/civil/view.do" in full_url and "civilId=" in full_url:
            links.append(full_url)

    return list(dict.fromkeys(links))


def extract_written_dates_from_text(text):
    return re.findall(r"(20\d{2})[-.](\d{2})[-.](\d{2})", text)

# 5년
def is_recent_5_years(text):
    dates = extract_written_dates_from_text(text)

    if not dates:
        return True

    years = [int(y) for y, _, _ in dates]
    return any(year >= MIN_YEAR for year in years)


def remove_noise(soup):
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    for selector in [
        "header", "footer", "nav", "aside",
        "#header", "#footer", "#gnb", "#lnb", "#snb",
        ".header", ".footer", ".gnb", ".lnb", ".snb",
        ".quickMenu", ".snsArea", ".shareArea", ".printArea",
    ]:
        for node in soup.select(selector):
            node.decompose()


def get_main_text(html):
    soup = BeautifulSoup(html, "html.parser")
    remove_noise(soup)

    candidates = [
        "#contents", "#content", ".contents", ".content",
        ".cntArea", ".sub_content", ".contArea",
        "main", "article", "body",
    ]

    best_node = None
    best_len = 0

    for selector in candidates:
        node = soup.select_one(selector)
        if not node:
            continue

        txt = node.get_text("\n", strip=True)
        if len(txt) > best_len:
            best_node = node
            best_len = len(txt)

    if not best_node:
        return ""

    return clean_text(best_node.get_text("\n", strip=True))


def cut_civil_body(text):
    start_idx = text.find("민원분야")
    if start_idx != -1:
        text = text[start_idx:]

    for stop in ["첨부파일", "목록", "만족도조사", "Quick Menu"]:
        idx = text.find(stop)
        if idx != -1:
            text = text[:idx]

    return clean_text(text)

# 저장조건
def is_target_civil_doc(doc):
    text = " ".join([
        doc.get("title", ""),
        doc.get("category", ""),
        doc.get("required_documents", ""),
        doc.get("notes", ""),
        doc.get("text", "")
    ])

    return any(keyword in text for keyword in TARGET_KEYWORDS)


def extract_title(text):
    text = clean_text(text)

    # 불필요한 공통 문구 제거
    noise_words = [
        "Home", "전자민원", "종합민원안내", "열기", "블로그",
        "인스타그램", "페이스북", "카카오", "닫기", "인쇄하기", "내용보기"
    ]
    for word in noise_words:
        text = text.replace(word, " ")

    text = clean_text(text)

    # 민원사무서식 - 대분류 - 실제제목 형태 처리
    match = re.search(r"민원사무서식\s*[-–]\s*(.+?)\s+민원분야", text)
    if match:
        title_part = clean_text(match.group(1))
        parts = [p.strip() for p in re.split(r"\s*[-–]\s*", title_part) if p.strip()]
        if parts:
            return parts[-1]

    # 민원분야 앞부분에서 마지막 '-' 뒤를 제목으로 사용
    before = text.split("민원분야")[0]
    parts = [p.strip() for p in re.split(r"\s*[-–]\s*", before) if p.strip()]
    if parts:
        return parts[-1]

    return "제목없음"


def parse_fields(body_text):
    compact = clean_text(body_text)
    result = {}

    for i, field in enumerate(FIELD_NAMES):
        start_match = re.search(re.escape(field), compact)

        if not start_match:
            result[field] = ""
            continue

        start = start_match.end()
        end = len(compact)

        for next_field in FIELD_NAMES[i + 1:]:
            next_match = re.search(re.escape(next_field), compact[start:])
            if next_match:
                end = start + next_match.start()
                break

        result[field] = clean_text(compact[start:end])

    return result


def make_plain_text(title, fields):
    parts = [f"제목: {title}"]

    for field in FIELD_NAMES:
        value = fields.get(field, "")
        if value:
            parts.append(f"{field}: {value}")

    return "\n".join(parts)


def parse_detail_page(url, html):
    main_text = get_main_text(html)
    body_text = cut_civil_body(main_text)

    if "민원분야" not in body_text:
        return None

    title = extract_title(main_text)
    fields = parse_fields(body_text)

    return {
        "doc_id": make_id(url),
        "url": url,
        "page_type": "civil_form_guide",
        "title": title,
        "category": fields.get("민원분야", ""),
        "department": fields.get("담당부서", ""),
        "phone": fields.get("담당자 전화번호", ""),
        "processing_period": fields.get("처리기간", ""),
        "required_documents": fields.get("신청서 및 구비서류", ""),
        "submission_place": fields.get("제출처", ""),
        "fee": fields.get("수수료 및 기타비용", ""),
        "notes": fields.get("유의사항", ""),
        "review_criteria": fields.get("행정기관의 심사기준", ""),
        "workflow": fields.get("업무처리 흐름도", ""),
        "appeal": fields.get("이의신청", ""),
        "etc": fields.get("기타", ""),
        "fields": fields,
        "text": make_plain_text(title, fields),
        "source": "saha.go.kr",
    }


def crawl_recent_civil_forms():
    ensure_dir(OUTPUT_DIR)

    session = requests.Session()
    saved = 0

    # 크롤링할 민원 페이지 범위 -> 일단 조금만
    START_CIVIL_ID = 2200
    END_CIVIL_ID = 2000

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for civil_id in range(START_CIVIL_ID, END_CIVIL_ID - 1, -1):
            url = f"https://www.saha.go.kr/portal/civil/view.do?civilId={civil_id}&mId=0103080100"
            print(f"[DETAIL] civilId={civil_id}")

            try:
                html = fetch(session, url)
                doc = parse_detail_page(url, html)
            except Exception as e:
                print(f"  요청/파싱 실패: {e}")
                continue

            if not doc:
                print("  저장 안 함")
                continue

            if not is_target_civil_doc(doc):
                print("  저장 안 함: 대상 민원 아님")
                continue

            # 최근 5년 필터용: 상세 본문에 날짜가 없으면 일단 저장
            out.write(json.dumps(doc, ensure_ascii=False) + "\n")
            saved += 1
            print(f"  저장 완료: {doc['title']}")

            time.sleep(REQUEST_DELAY)

    print("\n수집 완료")
    print(f"- 저장 문서 수: {saved}")
    print(f"- 저장 파일: {OUTPUT_FILE}")

if __name__ == "__main__":
    crawl_recent_civil_forms()