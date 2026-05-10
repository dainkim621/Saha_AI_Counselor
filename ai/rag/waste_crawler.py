import os
import re
import json
import time
import hashlib
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

OUTPUT_DIR = "data/raw"
OUTPUT_JSONL = os.path.join(OUTPUT_DIR, "saha_waste_docs.jsonl")

# 페이지 범위가 적어서 직접 URL 지정
TARGET_PAGES = [
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0405050000",
        "category": "생활폐기물처리안내",
        "topic": "생활쓰레기 배출요령",
    },
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0405050102",
        "category": "생활폐기물처리안내",
        "topic": "음식물쓰레기 배출요령",
    },
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0405050103",
        "category": "생활폐기물처리안내",
        "topic": "대형폐기물 처리 및 수수료",
    },
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0405050104",
        "category": "생활폐기물처리안내",
        "topic": "폐가전 무상처리 안내",
    },
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0405050700",
        "category": "사업장폐기물처리안내",
        "topic": "사업장폐기물 처리안내",
    },
]

HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15
REQUEST_DELAY = 0.7

NOISE_SELECTORS = [
    "header", "footer", "nav", "aside",
    "#header", "#footer", "#gnb", "#lnb", "#snb",
    ".header", ".footer", ".gnb", ".lnb", ".snb",
    ".skip", ".breadcrumbs", ".location", ".quick",
    ".snsArea", ".shareArea", ".printArea",
    ".satisfaction", ".survey", ".comment", ".reply",
    ".prevNext", ".boardBtn", ".btnArea", ".pagination",
    ".searchArea", ".tabMenu", ".banner", ".popupZone",
    ".viewer", ".copy", ".copyright",
    ".familySite", ".siteLink", ".util", ".topBanner",
]

CONTENT_SELECTORS = [
    "#contents", "#content", ".contents", ".content",
    ".cntArea", ".contArea", ".conBox", "main", "article"
]


def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    return text.strip()


def clean_inline(text):
    text = clean_text(text)
    return re.sub(r"\s+", " ", text).strip()


def make_doc_id(url):
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def get_mid(url):
    qs = parse_qs(urlparse(url).query)
    return qs.get("mId", [""])[0]


def remove_noise_nodes(soup):
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()


def extract_title(soup, fallback_title):
    if soup.title:
        raw = clean_inline(soup.title.get_text(" ", strip=True))
        parts = [clean_inline(p) for p in raw.split("|") if clean_inline(p)]
        if parts:
            return parts[0]
    return fallback_title


def extract_metadata(soup):
    full_text = soup.get_text("\n", strip=True)

    department = ""
    phone = ""
    date = ""
    views = ""

    # 담당부서/과
    m = re.search(
        r"(?:담당부서|부서)\s*[:：]?\s*([^\n]+)",
        full_text
    )
    if m:
        department = clean_inline(m.group(1))

    # 전화번호
    m = re.search(
        r"(0\d{1,2}-\d{3,4}-\d{4})",
        full_text
    )
    if m:
        phone = m.group(1)

    # 수정일
    m = re.search(
        r"(최근업데이트|최종수정일|수정일)\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        full_text
    )
    if m:
        date = m.group(2).replace(".", "-").replace("/", "-")

    # 조회수
    m = re.search(r"조회수\s*[:：]?\s*([\d,]+)", full_text)
    if m:
        views = m.group(1).replace(",", "")

    return {
        "department": department,
        "phone": phone,
        "date": date,
        "views": views,
    }


def select_main_content(soup):
    candidates = []

    for selector in CONTENT_SELECTORS:
        for node in soup.select(selector):
            text = clean_text(node.get_text("\n", strip=True))
            if len(text) >= 80:
                candidates.append((len(text), node))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        return candidates[0][1]

    return soup.body


def extract_tables_as_text(node):
    results = []

    for table in node.select("table"):
        rows = []

        for tr in table.find_all("tr"):
            cells = [
                clean_inline(cell.get_text(" ", strip=True))
                for cell in tr.find_all(["th", "td"])
            ]
            cells = [c for c in cells if c]

            if cells:
                rows.append(" | ".join(cells))

        if rows:
            results.append("[표]\n" + "\n".join(rows))

    return results


def extract_lists_as_text(node):
    results = []

    for ul in node.select("ul, ol"):
        items = []

        for li in ul.find_all("li", recursive=False):
            txt = clean_inline(li.get_text(" ", strip=True))
            if len(txt) >= 3:
                items.append("- " + txt)

        if items:
            results.append("[목록]\n" + "\n".join(items))

    return results


def extract_key_sections(text):
    """
    RAG 검색 정확도를 위해 배출방법/수수료/신고기준 관련 문장을 별도 필드로 뽑는다.
    """
    keywords = [
        "배출", "처리방법", "수수료", "가격", "종량제",
        "봉투", "전용용기", "납부필증", "칩",
        "무상수거", "위탁처리", "배출신고", "처리증명",
        "과태료", "업체", "전화"
    ]

    lines = [clean_inline(line) for line in text.splitlines()]
    lines = [line for line in lines if line]

    key_lines = []
    for line in lines:
        if any(k in line for k in keywords):
            key_lines.append(line)

    return key_lines


def extract_page(html, page_info):
    soup = BeautifulSoup(html, "html.parser")
    metadata_soup = BeautifulSoup(html, "html.parser")

    remove_noise_nodes(soup)

    title = extract_title(soup, page_info["topic"])
    main_node = select_main_content(soup)

    body_text = clean_text(main_node.get_text("\n", strip=True)) if main_node else ""

    table_blocks = extract_tables_as_text(main_node) if main_node else []
    list_blocks = extract_lists_as_text(main_node) if main_node else []

    menu_path = [
        "분야별정보",
        "환경/청소",
        "폐기물",
        page_info["category"],
        page_info["topic"],
    ]

    parts = [
        f"제목: {title}",
        "메뉴경로: " + " > ".join(menu_path),
        f"분류: {page_info['category']}",
        f"주제: {page_info['topic']}",
        "[본문]",
        body_text,
    ]

    if table_blocks:
        parts.append("[표 정보]")
        parts.extend(table_blocks)

    if list_blocks:
        parts.append("[목록 정보]")
        parts.extend(list_blocks)

    text = clean_text("\n\n".join(parts))
    paragraphs = [p for p in re.split(r"\n{2,}", text) if clean_inline(p)]

    metadata = extract_metadata(metadata_soup)
    key_sections = extract_key_sections(text)

    doc = {
        "doc_id": make_doc_id(page_info["url"]),
        "url": page_info["url"],
        "mId": get_mid(page_info["url"]),
        "parent_url": "https://www.saha.go.kr/portal/contents.do?mId=0405050000",
        "menu_path": menu_path,
        "page_type": "waste_guide",
        "category": page_info["category"],
        "topic": page_info["topic"],
        "title": title,
        "author": metadata.get("author", ""),
        "date": metadata.get("date", ""),
        "views": metadata.get("views", ""),
        "text": text,
        "paragraphs": paragraphs,
        "key_sections": key_sections,
        "source": "saha.go.kr",
        "department": metadata.get("department", ""),
        "phone": metadata.get("phone", "")
    }

    return doc


def crawl_waste_pages():
    ensure_dir(OUTPUT_DIR)

    session = requests.Session()
    session.headers.update(HEADERS)

    saved_count = 0

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for page in TARGET_PAGES:
            url = page["url"]
            print(f"[VISIT] {page['category']} / {page['topic']} / {url}")

            try:
                response = session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
            except Exception as e:
                print(f"  요청 실패: {e}")
                continue

            doc = extract_page(response.text, page)

            if len(doc["text"]) < 100:
                print(f"  저장 안 함: 본문 부족 | {doc['title']}")
                continue

            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            f.flush()

            saved_count += 1
            print(f"  저장 완료 ({saved_count}): {doc['title']}")
            print(f"  핵심문장 수: {len(doc['key_sections'])}")

            time.sleep(REQUEST_DELAY)

    print("\n폐기물 처리안내 크롤링 완료")
    print(f"- 저장 문서 수: {saved_count}")
    print(f"- 출력 파일: {OUTPUT_JSONL}")


if __name__ == "__main__":
    crawl_waste_pages()