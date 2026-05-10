import os
import re
import json
import time
import hashlib
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag, parse_qs

import requests
from bs4 import BeautifulSoup

# ==============================
# 설정
# ==============================
START_URLS = [

    "https://www.saha.go.kr/portal/contents.do?mId=0100000000",   # 전자민원 
    "https://www.saha.go.kr/portal/contents.do?mId=0200000000", # 구민참여
    "https://www.saha.go.kr/portal/contents.do?mId=0300000000", # 정보공개 


]

ALLOWED_DOMAINS = {"www.saha.go.kr", "m.saha.go.kr"}

OUTPUT_DIR = "data/raw"
OUTPUT_JSONL = os.path.join(OUTPUT_DIR, "saha_docs.jsonl")

MAX_PAGES = 1000   # 여기 양 조절하기
REQUEST_DELAY = 0.8
TIMEOUT = 15

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}

DENY_URL_KEYWORDS = [
    "javascript:",
    "login",
    "logout",
    "sitemap",
    "popup",
    "calendar",
    "youtube",
    "blog",
    "facebook",
    "instagram",
    "twitter",
    "kakao",
    "share",
    "print",
    "download",
    "viewer",
    "filedown",
]

# 현재 사하구청 전자민원 하위에서 의미 있는 경로만 추적
ALLOWED_PATH_KEYWORDS = [
    "/portal/contents.do",
    "/portal/bbs/list.do",
    "/portal/bbs/view.do",
    "/portal/civil/list.do",
    "/portal/civil/view.do",
]

# 저장 후보 경로
SAVE_CANDIDATE_KEYWORDS = [
    "/portal/contents.do",
    "/portal/bbs/view.do",
    "/portal/civil/view.do",
]

# 실제 본문 외 노이즈 제거용
NOISE_SELECTORS = [
    "header", "footer", "nav", "aside",
    "#header", "#footer", "#gnb", "#lnb", "#snb",
    ".header", ".footer", ".gnb", ".lnb", ".snb",
    ".skip", ".breadcrumbs", ".location", ".quick",
    ".quickMenu", "#quickMenu", ".subMenu", ".menuArea",
    ".snsArea", ".shareArea", ".printArea",
    ".relation", ".related", ".attach", ".file",
    ".satisfaction", ".survey", ".comment", ".reply",
    ".prevNext", ".boardBtn", ".btnArea", ".pagination",
    ".searchArea", ".tabMenu", ".banner", ".popupZone",
    ".department", ".charge", ".contact", ".infoBox",
    ".viewer", ".copy", ".copyright",
    ".familySite", ".siteLink", ".util", ".topBanner",
]
# 실제 본문 제목이 들어있는 영역을 더 넓게 찾도록 수정
TITLE_SELECTORS = [
    "h1",
    "h2",
    "h3",
    ".contTitle",
    ".pageTitle",
    ".subject",
    ".conTit",
    ".view_tit",
    ".board_tit",
    ".bbsTitle",
    ".titArea h3",
    ".contents h3",
]
#작성자
AUTHOR_SELECTORS = [
    ".writer", ".author", ".name", ".user",
    ".view_writer", ".board_writer"
]
#날짜
DATE_SELECTORS = [
    ".date", ".regDate", ".writeDate", ".view_date",
    ".board_date", ".bbs_date"
]
#조회수
VIEWS_SELECTORS = [
    ".view", ".hit", ".count", ".views",
    ".board_hit", ".view_count"
]

CONTENT_SELECTORS = [
    "#contents",
    "#content",
    ".contents",
    ".content",
    ".cntArea",
    ".sub_content",
    ".contArea",
    ".article",
    ".board_view",
    ".view_cont",
    ".conBox",
    "main",
    "article",
]

META_AUTHOR_SELECTORS = [
    ".writer", ".author", ".name", ".user", ".department", ".charge", ".manager"
]
META_DATE_SELECTORS = [
    ".date", ".regDate", ".writeDate", ".created", ".updated", ".day"
]
META_VIEWS_SELECTORS = [
    ".view", ".views", ".hit", ".count", ".readCnt"
]

SECTION_HINTS = [
    "신청대상", "신청방법", "처리절차", "처리기간", "수수료",
    "구비서류", "제출서류", "유의사항", "문의처", "신고기한",
    "온라인 신청", "방문 신청"
]

BAD_TEXT_SIGNALS = [
    "주메뉴", "사하구 홈페이지", "저작권", "개인정보처리방침",
    "만족도 조사", "이전글", "다음글", "목록", "공유", "프린트",
    "비주얼 홍보 이미지", "이전 이미지", "다음 이미지",
]

MENU_SIGNALS = [
    "비주얼 홍보 이미지", "이전 이미지", "다음 이미지", "퀵아이콘",
    "우리동 소식", "등록된 게시물이 없습니다", "사하구 홈페이지",
    "전자민원", "정보공개", "분야별 정보", "주메뉴",
    "만족도 조사", "개인정보처리방침", "저작권", "사이트맵",
    "이전글", "다음글", "목록", "공유", "프린트"
]

# 메뉴 prefix 기반 관리
ALLOWED_MENU_PREFIXES = {
    "01": "전자민원",
    "02": "구민참여",
    "03": "정보공개",
}


# ==============================
# 유틸
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


def normalize_url(base_url: str, href: str):
    if not href:
        return None

    href = href.strip()
    if href.startswith(("javascript:", "mailto:", "tel:")):
        return None

    full_url = urljoin(base_url, href)
    full_url, _ = urldefrag(full_url)

    parsed = urlparse(full_url)
    if parsed.scheme not in ("http", "https"):
        return None
    if parsed.netloc not in ALLOWED_DOMAINS:
        return None

    return full_url


def is_html_response(response: requests.Response) -> bool:
    content_type = response.headers.get("Content-Type", "")
    return "text/html" in content_type.lower()


def url_to_id(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def clean_meta_value(value: str) -> str:
    if not value:
        return ""
    value = clean_text(value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def normalize_date(value: str) -> str:
    value = clean_meta_value(value)
    if not value:
        return ""

    m = re.search(r"(20\d{2})[./-]\s*(\d{1,2})[./-]\s*(\d{1,2})", value)
    if m:
        y, mo, d = m.groups()
        return f"{y}-{int(mo):02d}-{int(d):02d}"

    return value


def normalize_views(value: str):
    value = clean_meta_value(value)
    if not value:
        return None

    m = re.search(r"(\d[\d,]*)", value)
    if not m:
        return None

    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


# ==============================
# URL / 페이지 타입 판별
# ==============================
def is_portal_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc in ALLOWED_DOMAINS and parsed.path.startswith("/portal/")

ALLOWED_MID_PREFIXES = {
    "01": "전자민원",
    "02": "정보공개",
    "03": "분야별정보",
}
# 전자민원 전용함수 -> 전체민원 함수

def has_allowed_mid(url: str) -> bool:
    try:
        qs = parse_qs(urlparse(url).query)
        mid = qs.get("mId", [""])[0]
        return len(mid) >= 2 and mid[:2] in ALLOWED_MENU_PREFIXES
    except Exception:
        return False
    """
    #현재 전자민원 계열은 mId가 01로 시작하는 경우가 많음.
    def is_ecivil_mid(url: str) -> bool:
        try:
            qs = parse_qs(urlparse(url).query)
            mid = qs.get("mId", [""])[0]
            return mid.startswith("01")
        except Exception:
            return False
    """


def classify_page_type(url: str) -> str:
    lower_url = url.lower()

    if "/portal/bbs/list.do" in lower_url:
        return "bbs_list"
    if "/portal/bbs/view.do" in lower_url:
        return "bbs_view"
    if "/portal/civil/list.do" in lower_url:
        return "civil_list"
    if "/portal/civil/view.do" in lower_url:
        return "civil_view"
    if "/portal/contents.do" in lower_url:
        return "contents"
    return "other"

# 저장 여부 판단을 위해 URL 저장하는 함수
# 대표 제목만 확인하고 저장하지 않은 뒤 넘어가고, 게시글 전체 목록을 깊게 타지 않음
def should_visit(url: str) -> bool:
    lower_url = url.lower()

    if any(x in lower_url for x in DENY_URL_KEYWORDS):
        return False

    if not is_portal_url(url):
        return False

    if not any(x in lower_url for x in ALLOWED_PATH_KEYWORDS):
        return False

    page_type = classify_page_type(url)

    if page_type == "contents":
        return has_allowed_mid(url)

    # 목록 페이지는 방문만 허용, 저장은 should_save에서 막음
    if page_type in ("bbs_list", "civil_list"):
        return True

    # 상세 게시글은 현재 단계에서는 탐색하지 않음
    return False

# 목록 페이지는 저장하지 않음
# 단, crawl()에서 링크 수집은 계속 하므로 하위 링크 탐색은 가능
def should_save(url: str) -> bool:
    page_type = classify_page_type(url)

    if page_type in ("bbs_list", "civil_list"):
        return False

    # 상세/일반 안내 페이지만 저장 후보
    if page_type in ("bbs_view", "civil_view"):
        return True

    if page_type == "contents":
        return has_allowed_mid(url)

    return False

# ==============================
# 링크 수집
# ==============================

"""
링크를 수집할 때, URL만 저장하지 않고
- 부모 URL
- 앵커 텍스트
- 메뉴 경로
도 같이 저장해서 나중에 문서 점수에 활용
"""

def extract_links_from_raw_html(html: str, current_url: str, parent_menu_path=None):
    if parent_menu_path is None:
        parent_menu_path = []

    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):
        normalized = normalize_url(current_url, a["href"])
        if not normalized:
            continue
        if not should_visit(normalized):
            continue

        anchor_text = clean_text(a.get_text(" ", strip=True))
        menu_path = list(parent_menu_path)

        if anchor_text and anchor_text not in menu_path and len(anchor_text) <= 40:
            menu_path = menu_path + [anchor_text]

        links.append({
            "url": normalized,
            "parent_url": current_url,
            "anchor_text": anchor_text,
            "menu_path": menu_path,
        })

    # dedup
    dedup = {}
    for item in links:
        url = item["url"]

        if url not in dedup:
            dedup[url] = item
        else:
            prev = dedup[url]
            if len(item["menu_path"]) > len(prev["menu_path"]):
                dedup[url] = item

    return list(dedup.values())

# ==============================
# 본문 추출
# ==============================
def remove_noise_nodes(soup: BeautifulSoup):
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()

# soup.title fallback을 그대로 쓰지 말고 필터링
def is_generic_site_title(title: str) -> bool:
    lower_title = title.lower()
    generic_patterns = [
        "saha district office",
        "사하구 홈페이지",
    ]
    return any(p in lower_title for p in generic_patterns)


def is_generic_site_title(title: str) -> bool:
    if not title:
        return True

    lower = title.lower()
    generic_patterns = [
        "saha district office",
        "사하구 홈페이지",
        "부산광역시 사하구",
    ]

    # "구민참여 Saha District Office" 같은 공통 제목 제거
    return any(p in lower for p in generic_patterns) and "|" not in title

def is_bad_title(title: str) -> bool:
    bad_titles = [
        "서브 메뉴",
        "메뉴",
        "주메뉴",
        "사이트맵",
        "검색",
        "공유",
        "프린트",
    ]

    if not title:
        return True

    title = title.strip()

    # 완전 동일한 경우
    if title in bad_titles:
        return True

    # 사이트 공통 제목 제거
    if "Saha District Office" in title:
        return True

    return False


def extract_title_from_browser_title(soup: BeautifulSoup) -> str:
    """
    <title>주민참여예산 알림방 목록 | 주민참여예산 | 구민참여 | 부산광역시 사하구</title>
    같은 경우 첫 번째 항목만 대표 제목으로 사용
    """
    if not soup.title:
        return ""

    raw = clean_text(soup.title.get_text(" ", strip=True))
    if not raw:
        return ""

    parts = [clean_text(p) for p in raw.split("|") if clean_text(p)]
    if parts:
        title = parts[0]
        title = re.sub(r"\s*목록\s*$", "", title).strip()
        title = re.sub(r"\s*상세\s*$", "", title).strip()
        if 2 <= len(title) <= 120:
            return title

    if not is_generic_site_title(raw) and 2 <= len(raw) <= 120:
        return raw

    return ""


def extract_title(soup: BeautifulSoup) -> str:
    # 1. title 태그에서 먼저 실제 제목 추출
    # 예: 주요행사안내 | 정보공개 | 부산광역시 사하구
    if soup.title:
        raw_title = clean_text(soup.title.get_text(" ", strip=True))
        parts = [p.strip() for p in raw_title.split("|") if p.strip()]

        if parts:
            candidate = parts[0]
            candidate = re.sub(r"\s*목록\s*$", "", candidate).strip()
            candidate = re.sub(r"\s*상세\s*$", "", candidate).strip()

            if 2 <= len(candidate) <= 120 and not is_bad_title(candidate):
                return candidate

    # 2. 본문 제목 selector 탐색
    for selector in TITLE_SELECTORS:
        node = soup.select_one(selector)
        if node:
            txt = clean_text(node.get_text(" ", strip=True))
            txt = re.sub(r"\s*목록\s*$", "", txt).strip()
            txt = re.sub(r"\s*상세\s*$", "", txt).strip()

            if 2 <= len(txt) <= 120 and not is_bad_title(txt):
                return txt

    # 3. 마지막 fallback: 본문 첫 줄
    main_node = select_main_content(soup)
    if main_node:
        lines = [
            clean_text(x)
            for x in main_node.get_text("\n", strip=True).split("\n")
        ]

        for line in lines:
            line = re.sub(r"\s*목록\s*$", "", line).strip()
            line = re.sub(r"\s*상세\s*$", "", line).strip()

            if 2 <= len(line) <= 80 and not is_bad_title(line):
                return line

    return ""

def extract_first_match_text(soup, selectors, min_len=1, max_len=100):
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            txt = clean_text(node.get_text(" ", strip=True))
            if min_len <= len(txt) <= max_len:
                return txt
    return ""


def extract_first_by_selectors(soup: BeautifulSoup, selectors):
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            txt = clean_meta_value(node.get_text(" ", strip=True))
            if txt:
                return txt
    return ""


def extract_meta_by_regex(full_text: str, patterns):
    if not full_text:
        return ""

    for pattern in patterns:
        m = re.search(pattern, full_text, flags=re.IGNORECASE)
        if m:
            value = clean_meta_value(m.group(1))
            if value:
                return value
    return ""

def extract_metadata(soup: BeautifulSoup):
    """
    하단 담당자 / 최근업데이트 / 조회수 추출
    - contents 페이지: 하단의 담당자, 최근업데이트 중심
    - bbs view 페이지: 작성자/등록일/조회수 중심
    """
    full_text = soup.get_text("\n", strip=True)

    author = ""
    date = ""
    views = ""

    # 1. 하단 담당자 추출
    # 예: 담당자 : 홍길동 / 담당부서 : 민원여권과 / 콘텐츠 관리부서 : ...
    author_patterns = [
        r"담당자\s*[:：]?\s*([^\n|]+)",
        r"콘텐츠\s*관리부서\s*[:：]?\s*([^\n|]+)",
        r"담당부서\s*[:：]?\s*([^\n|]+)",
        r"부서\s*[:：]?\s*([^\n|]+)",
        r"작성자\s*[:：]?\s*([^\n|]+)",
    ]

    for pattern in author_patterns:
        m = re.search(pattern, full_text)
        if m:
            author = clean_meta_value(m.group(1))
            break

    # 2. 최근업데이트 / 최종수정일 / 등록일 추출
    # "최근업데이트" 같은 라벨만 저장하지 않고 실제 날짜만 저장
    date_patterns = [
        r"최근업데이트\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"최종수정일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"수정일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"등록일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"작성일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"게시일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
    ]

    for pattern in date_patterns:
        m = re.search(pattern, full_text)
        if m:
            date = normalize_date(m.group(1))
            break

    # 3. 조회수 추출
    view_patterns = [
        r"조회수\s*[:：]?\s*([\d,]+)",
        r"조회\s*[:：]?\s*([\d,]+)",
        r"조회\s+([\d,]+)",
    ]

    for pattern in view_patterns:
        m = re.search(pattern, full_text)
        if m:
            views = normalize_views(m.group(1))
            break

    return {
        "author": author,
        "date": date,
        "views": views,
    }

def score_node_text(text: str) -> int:
    """
    키워드 하드코딩보다, 문서가 '설명형/민원형'으로 보이는지 점수화
    """
    score = 0

    # 섹션 구조가 보이면 가점
    for kw in SECTION_HINTS:
        if kw in text:
            score += 2

    # 안내형 텍스트는 어느 정도 길이가 있어야 함
    score += min(len(text) // 250, 8)

    # 메뉴/홍보/푸터 신호가 많으면 감점
    for kw in BAD_TEXT_SIGNALS:
        if kw in text:
            score -= 2

    return score


def select_main_content(soup: BeautifulSoup):
    candidates = []

    for selector in CONTENT_SELECTORS:
        for node in soup.select(selector):
            text = clean_text(node.get_text("\n", strip=True))
            if len(text) < 80:
                continue

            score = score_node_text(text)
            candidates.append((score, len(text), node))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]


def remove_noise_lines(text: str) -> str:
    lines = []

    NOISE_LINE_PATTERNS = [
        r"^이전글.*",
        r"^다음글.*",
        r"^목록.*",
        r"^SNS.*공유.*",
        r"^공유.*",
        r"^프린트.*",
        r"^저작권.*",
        r"^개인정보처리방침.*",
        r"^만족도 조사.*",
        r"^페이지 만족도.*",
        r"^담당부서.*",
        r"^조회수.*",
        r"^등록일.*",
        r"^수정일.*",
        r"^첨부파일.*",
        r"^뷰어다운로드.*",
        r"^주메뉴.*",
        r"^통합검색.*",
        r"^홈페이지 의견수렴.*",
        r"^관련사이트.*",
        r"^콘텐츠 관리부서.*",
        r"^최종수정일.*",
    ]

    for line in text.split("\n"):
        line = clean_text(line)
        if not line:
            continue

        skip = False
        for pattern in NOISE_LINE_PATTERNS:
            if re.match(pattern, line):
                skip = True
                break

        if skip:
            continue

        if len(line) <= 1:
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def extract_tables_as_text(node) -> list[str]:
    """
    표 구조를 문장형 텍스트로 풀어서 저장.
    민원편람/서식안내, 자주찾는 민원서식 작성예시처럼
    표 기반 페이지를 살리기 위해 중요함.
    """
    table_texts = []

    for table in node.select("table"):
        headers = []
        thead = table.find("thead")
        if thead:
            headers = [clean_text(th.get_text(" ", strip=True)) for th in thead.find_all(["th", "td"])]

        rows_out = []
        tbody_rows = table.find_all("tr")
        for tr in tbody_rows:
            cells = [clean_text(td.get_text(" ", strip=True)) for td in tr.find_all(["th", "td"])]
            cells = [c for c in cells if c]
            if not cells:
                continue

            if headers and len(headers) == len(cells):
                merged = [f"{h}: {c}" for h, c in zip(headers, cells) if h and c]
                row_text = " | ".join(merged)
            else:
                row_text = " | ".join(cells)

            if len(row_text) >= 10:
                rows_out.append(row_text)

        if rows_out:
            table_texts.append("[표]\n" + "\n".join(rows_out))

    return table_texts


def extract_list_as_text(node) -> list[str]:
    """
    ul/ol/dl 도 의미 있는 안내문인 경우가 많아서 텍스트로 변환
    """
    results = []

    for ul in node.select("ul, ol"):
        items = []
        for li in ul.find_all("li", recursive=False):
            txt = clean_text(li.get_text(" ", strip=True))
            if len(txt) >= 5:
                items.append(f"- {txt}")
        if items:
            results.append("[목록]\n" + "\n".join(items))

    for dl in node.select("dl"):
        items = []
        dts = dl.find_all("dt")
        dds = dl.find_all("dd")
        for dt, dd in zip(dts, dds):
            dt_txt = clean_text(dt.get_text(" ", strip=True))
            dd_txt = clean_text(dd.get_text(" ", strip=True))
            if dt_txt and dd_txt:
                items.append(f"{dt_txt}: {dd_txt}")
        if items:
            results.append("[정의목록]\n" + "\n".join(items))

    return results


def build_structured_text(title: str, body_text: str, extra_blocks: list[str], menu_path=None) -> str:
    parts = []

    if title:
        parts.append(f"제목: {title}")

    if menu_path:
        parts.append("메뉴경로: " + " > ".join(menu_path))

    if body_text:
        parts.append("[본문]")
        parts.append(body_text)

    if extra_blocks:
        parts.append("[구조정보]")
        parts.extend(extra_blocks)

    return clean_text("\n\n".join(parts))


def split_paragraphs(text: str):
    parts = re.split(r"\n{2,}", text)
    results = []

    for part in parts:
        part = clean_text(part)
        if len(part) >= 30:
            results.append(part)

    return results


def is_menu_like_text(text: str) -> bool:
    hit = sum(1 for x in MENU_SIGNALS if x in text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    line_count = len(lines)
    short_line_count = sum(1 for line in lines if len(line) <= 12)

    if hit >= 3:
        return True

    if line_count > 0 and (short_line_count / line_count) > 0.60:
        return True

    return False


def document_score(url: str, title: str, text: str, menu_path=None, anchor_text="") -> int:
    """
    저장 여부를 최종 판단하는 점수 함수.
    메뉴 이름 하드코딩 없이,
    '이 페이지가 실제 설명형 문서인가'를 기준으로 점수화한다.
    문서 구조 / 페이지 유형 / 링크 문맥 존재 여부만 점수화
    """
    score = 0
    page_type = classify_page_type(url)
    menu_path = menu_path or []

    # 1) 페이지 유형 점수
    # 상세 페이지는 가점, 목록 페이지는 감점
    if page_type in ("bbs_view", "civil_view"):
        score += 3
    elif page_type == "contents":
        score += 2
    elif page_type in ("bbs_list", "civil_list"):
        score -= 3

    # 2) 제목 품질
    # 제목이 너무 짧거나 비정상이 아니면 소폭 가점
    if 2 <= len(title) <= 120:
        score += 1

    # 3) 본문 길이
    # 설명형 문서는 어느 정도 길이가 있어야 함
    if len(text) >= 200:
        score += 2
    if len(text) >= 500:
        score += 2
    if len(text) >= 1000:
        score += 1

    # 4) 안내문 구조 점수
    # 신청방법, 처리기간 같은 실제 안내 섹션이 있으면 가점
    section_hits = sum(1 for kw in SECTION_HINTS if kw in text)
    score += min(section_hits * 2, 6)

    # 5) 표/목록/정의목록 같은 구조 정보 가점
    # 사하구청 민원/안내 페이지는 표나 목록 기반 설명이 많아서 반영
    structure_hits = 0
    if "[표]" in text:
        structure_hits += 1
    if "[목록]" in text:
        structure_hits += 1
    if "[정의목록]" in text:
        structure_hits += 1
    score += min(structure_hits, 3)

    # 6) 메뉴성 페이지 감점
    # 메인/허브/배너성 페이지면 크게 감점
    if is_menu_like_text(text):
        score -= 4

    # 7) 링크 문맥 점수
    # 메뉴 이름 하드코딩 없이:
    # 상위 메뉴 경로가 존재하고, anchor_text가 있으면 문서형일 가능성이 올라감
    if menu_path:
        score += min(len(menu_path), 3)

    if anchor_text and len(anchor_text.strip()) >= 2:
        score += 1

    # 허브/목록 페이지는 저장하지 않도록 더 강한 감점
    if page_type in ("bbs_list", "civil_list"):
        score -= 5

    if "[표]" not in text and "[목록]" not in text and "[정의목록]" not in text:
        section_hits = sum(1 for kw in SECTION_HINTS if kw in text)
        if section_hits == 0 and len(text) < 400:
            score -= 2

    return score


def extract_text(html: str, menu_path=None):
    soup = BeautifulSoup(html, "html.parser")
    remove_noise_nodes(soup)

    title = extract_title(soup)
    main_node = select_main_content(soup)

    if main_node is None:
        return title, "", []

    raw_body = clean_text(main_node.get_text("\n", strip=True))
    raw_body = remove_noise_lines(raw_body)

    # 표/목록/정의목록도 구조 정보로 같이 저장
    extra_blocks = []
    extra_blocks.extend(extract_tables_as_text(main_node))
    extra_blocks.extend(extract_list_as_text(main_node))

    raw_text = build_structured_text(title, raw_body, extra_blocks, menu_path=menu_path)
    paragraphs = split_paragraphs(raw_text)

    return title, raw_text, paragraphs

# 메뉴이름, 3개만 하드코딩된
def get_menu_name_from_url(url: str):
    if "mId=01" in url:
        return "전자민원"
    elif "mId=02" in url:
        return "구민참여"
    elif "mId=03" in url:
        return "정보공개"
    return "기타"
# ==============================
# 크롤링
# ==============================
def crawl():
    ensure_dir(OUTPUT_DIR)

    session = requests.Session()
    session.headers.update(HEADERS)

    visited = set()
    queued = set()
    queue = deque()

    for url in START_URLS:
        menu_name = get_menu_name_from_url(url)
        item = {
            "url": url,
            "parent_url": "",
            "anchor_text": menu_name,
            "menu_path": [menu_name],
        }
        queue.append(item)
        queued.add(url)

    saved_count = 0

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        while queue and len(visited) < MAX_PAGES:
            item = queue.popleft()
            url = item["url"]
            parent_url = item.get("parent_url", "")
            anchor_text = item.get("anchor_text", "")
            menu_path = item.get("menu_path", [])

            if url in visited:
                continue

            visited.add(url)
            print(f"[VISIT] {url}")

            try:
                response = session.get(url, timeout=TIMEOUT)
                response.raise_for_status()
            except Exception as e:
                print(f"  요청 실패: {e}")
                continue

            if not is_html_response(response):
                print("  HTML 아님, 스킵")
                continue

            html = response.text

            # 링크는 저장 여부와 상관없이 먼저 수집
            links = extract_links_from_raw_html(html, url, parent_menu_path=menu_path) or []

            if not should_save(url):
                try:
                    soup_tmp = BeautifulSoup(html, "html.parser")
                    page_title = extract_title(soup_tmp)

                    print("  저장 안 함: 목록/허브 페이지")
                    print(f"  대표 제목: {page_title}")

                except Exception as e:
                    print(f"  저장 안 함 (파싱 실패): {e}")

            else:
                try:
                    title, raw_text, paragraphs = extract_text(html, menu_path=menu_path)

                    soup_for_meta = BeautifulSoup(html, "html.parser")
                    metadata = extract_metadata(soup_for_meta)

                    score = document_score(
                        url=url,
                        title=title,
                        text=raw_text,
                        menu_path=menu_path,
                        anchor_text=anchor_text,
                    )

                    print(f"  제목: {title}")
                    print(f"  본문 길이: {len(raw_text)}")
                    print(f"  문단 수: {len(paragraphs)}")
                    print(f"  문서 점수: {score}")

                    # ✅ 실제 저장 코드
                    # 지금은 먼저 저장이 되는지 확인하는 단계라 조건을 너무 빡세게 잡지 않음
                    if raw_text and len(raw_text) >= 80:
                        doc = {
                            "doc_id": url_to_id(url),
                            "url": url,
                            "parent_url": parent_url,
                            "anchor_text": anchor_text,
                            "menu_path": menu_path,
                            "page_type": classify_page_type(url),
                            "title": title,
                            "author": metadata.get("author", ""),
                            "date": metadata.get("date", ""),
                            "views": metadata.get("views", ""),
                            "text": raw_text,
                            "paragraphs": paragraphs,
                            "source": "saha.go.kr",
                        }

                        f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                        f.flush()

                        saved_count += 1
                        print(f"  저장 완료 ({saved_count}): {title if title else '제목없음'}")

                    else:
                        print("  저장 안 함: 본문 부족")

                except Exception as e:
                    print(f"  파싱 실패: {e}")

            added = 0
            for link in links:
                link_url = link["url"]
                if link_url not in visited and link_url not in queued:
                    queue.append(link)
                    queued.add(link_url)
                    added += 1

            print(f"  링크 추가: {added}개")
            time.sleep(REQUEST_DELAY)

    print("\n크롤링 완료")
    print(f"- 방문 페이지 수: {len(visited)}")
    print(f"- 저장 문서 수: {saved_count}")
    print(f"- 출력 파일: {OUTPUT_JSONL}")

if __name__ == "__main__": 
    crawl()