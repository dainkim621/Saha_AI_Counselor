import os
import re
import json
import time
import hashlib
from collections import deque
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlparse, urldefrag, parse_qs

import requests
from bs4 import BeautifulSoup, NavigableString, Tag

# =========================================================
# 설정
# =========================================================
OUTPUT_DIR = "data/raw"
OUTPUT_JSONL = os.path.join(OUTPUT_DIR, "saha_docs.jsonl")

MAX_PAGES = 100
MAX_BOARD_PAGES_PER_LIST = 10
REQUEST_DELAY = 0.7
TIMEOUT = 15

# 게시판 작성일 필터
CURRENT_YEAR = 2026
RECENT_DAYS = 365
RECENT_CUTOFF = datetime(CURRENT_YEAR, 5, 13) - timedelta(days=RECENT_DAYS)

# contents.do 안에서 연도별 메뉴 탐색용 기준
YEAR_MENU_LIMIT = 5
CURRENT_YEAR = 2026
MIN_YEAR_MENU = CURRENT_YEAR - YEAR_MENU_LIMIT + 1

ALLOWED_DOMAINS = {"www.saha.go.kr", "m.saha.go.kr"}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
}
# 제외 키워드
SHORTCUT_DENY_TEXTS = [
    "블로그", "인스타그램", "페이스북", "카카오",
    "트위터", "유튜브", "공유", "SNS",
    "맨처음페이지", "처음페이지", "이전페이지", "다음페이지",
    "10페이지 앞으로", "10페이지 뒤로", "맨끝페이지",
    "글쓰기", "수정", "삭제", "답글", "목록",
    "검색", "확인", "취소", "로그인", "로그아웃",
]

SHORTCUT_ALLOW_TEXTS = [
    "계약정보공개",
    "재정정보공개",
    "입찰정보",
    "전자민원창구",
    "정부24",
    "민원접수",
    "신청",
    "조회",
    "예약",
    "발급",
    "바로가기",
]

# ---------------------------------------------------------
# 시작 URL
# ---------------------------------------------------------
START_URLS = [
    # 전자민원: 예시 페이지가 전자민원이라 일단 포함
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0100000000",
        "menu_path": ["전자민원"],
        "scope": "전자민원",
    },

    # 구민참여: 신고센터만
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0203000000",
        "menu_path": ["구민참여", "신고센터"],
        "scope": "구민참여/신고센터",
    },

    # 정보공개: 사하알림, 행정정보공개
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0301000000",
        "menu_path": ["정보공개", "사하알림"],
        "scope": "정보공개/사하알림",
    },
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0302000000",
        "menu_path": ["정보공개", "행정정보공개"],
        "scope": "정보공개/행정정보공개",
    },

    # 사하소개: 청사안내만
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0605000000",
        "menu_path": ["사하소개", "청사안내"],
        "scope": "사하소개/청사안내",
    },

    # 분야별정보: 체육시설, 구민교육 제외는 아래 EXCLUDE_MID_PREFIXES에서 처리
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0400000000",
        "menu_path": ["분야별정보"],
        "scope": "분야별정보",
    },

    # 사하복지: 관련정보, 희망복지지원단, 사하구장학회, 후원 및 기부 제외는 아래에서 처리
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0500000000",
        "menu_path": ["사하복지"],
        "scope": "사하복지",
    },
]

# 허용할 큰 메뉴 prefix
ALLOWED_MID_PREFIXES = {
    "01": "전자민원",
    "02": "구민참여",
    "03": "정보공개",
    "04": "분야별정보",
    "05": "사하복지",
    "06": "사하소개",
}

# 제외할 메뉴 prefix
# 정확한 mId는 사이트 메뉴를 보고 다르면 여기만 수정하면 됨
EXCLUDE_MID_PREFIXES = [
    # 분야별정보 제외: 체육시설, 구민교육
    # 예시값이므로 실제 mId가 다르면 수정
    "0407",  # 체육시설 후보
    "0408",  # 구민교육 후보

    # 사하복지 제외: 관련정보, 희망복지지원단, 사하구장학회, 후원 및 기부
    # 예시값이므로 실제 mId가 다르면 수정
    "0503",
    "0505",
    "0507",
    "0508"
]

# 반드시 허용하고 싶은 개별 URL이나 mId가 있으면 여기에 추가
FORCE_ALLOW_MIDS = {
    "0103010000",  # 주민등록등·초본 예시 페이지
}

ALLOWED_PATH_KEYWORDS = [
    "/portal/contents.do",
    "/portal/bbs/list.do",
    "/portal/bbs/view.do",
    "/portal/civil/list.do",
    "/portal/civil/view.do",
]

DENY_URL_KEYWORDS = [
    "javascript:", "mailto:", "tel:",
    "login", "logout", "sitemap", "popup", "calendar",
    "youtube", "blog", "facebook", "instagram", "twitter", "kakao",
    "share", "print", "viewer", "filedown", "download",
]

NOISE_SELECTORS = [
    "script", "style", "noscript", "iframe", "svg",
    "header", "footer", "nav", "aside",
    "#header", "#footer", "#gnb", "#lnb", "#snb",
    ".header", ".footer", ".gnb", ".lnb", ".snb",
    ".skip", ".breadcrumbs", ".location", ".quick", ".quickMenu", "#quickMenu",
    ".snsArea", ".shareArea", ".printArea",
    ".satisfaction", ".survey", ".comment", ".reply",
    ".prevNext", ".boardBtn", ".btnArea", ".pagination",
    ".searchArea", ".banner", ".popupZone",
    ".viewer", ".copy", ".copyright", ".familySite", ".siteLink",
    ".util", ".topBanner",
]

# tabMenu는 직접 클릭형 하위 메뉴일 수 있어서 제거하지 않음
CONTENT_SELECTORS = [
    "#contents", "#content", ".contents", ".content",
    ".cntArea", ".sub_content", ".contArea", ".article",
    ".board_view", ".view_cont", ".conBox", "main", "article",
]

TITLE_SELECTORS = [
    "h1", "h2", "h3", ".contTitle", ".pageTitle", ".subject",
    ".conTit", ".view_tit", ".board_tit", ".bbsTitle",
    ".titArea h3", ".contents h3",
]

SECTION_TAGS = ["h1", "h2", "h3", "h4", "h5", "strong", "dt"]

SECTION_HINTS = [
    "신청대상", "신청방법", "처리절차", "처리기간", "수수료",
    "구비서류", "제출서류", "유의사항", "문의처", "신고기한",
    "온라인 신청", "방문 신청", "담당부서", "전화번호",
]

MENU_SIGNALS = [
    "비주얼 홍보 이미지", "이전 이미지", "다음 이미지", "퀵아이콘",
    "사하구 홈페이지", "주메뉴", "만족도 조사", "개인정보처리방침",
    "저작권", "사이트맵", "공유", "프린트",
]

# =========================================================
# 기본 유틸
# =========================================================
def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def clean_text(text):
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+\n", "\n", text)
    return text.strip()


def clean_inline(text):
    text = clean_text(text)
    return re.sub(r"\s+", " ", text).strip()


def clean_block_text(text):
    if not text:
        return ""

    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\r", "\n", text)
    text = re.sub(r"\n[ \t]*\n+", "\n", text)

    lines = []
    for line in text.split("\n"):
        line = clean_inline(line)
        if line:
            lines.append(line)

    return "\n".join(lines)


def url_to_id(url):
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def is_html_response(response):
    content_type = response.headers.get("Content-Type", "")
    return "text/html" in content_type.lower() or content_type == ""


def normalize_date(value):
    value = clean_inline(value)
    if not value:
        return ""
    m = re.search(r"(20\d{2})[./-]\s*(\d{1,2})[./-]\s*(\d{1,2})", value)
    if not m:
        return value
    y, mo, d = m.groups()
    return f"{y}-{int(mo):02d}-{int(d):02d}"


def parse_date(value):
    value = normalize_date(value)
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except Exception:
        return None


def normalize_views(value):
    value = clean_inline(value)
    m = re.search(r"(\d[\d,]*)", value)
    if not m:
        return None
    try:
        return int(m.group(1).replace(",", ""))
    except ValueError:
        return None


def normalize_url(base_url, href):
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


def get_mid(url):
    try:
        qs = parse_qs(urlparse(url).query)
        return qs.get("mId", [""])[0]
    except Exception:
        return ""


def classify_page_type(url):
    lower = url.lower()
    if "/portal/bbs/list.do" in lower:
        return "bbs_list"
    if "/portal/bbs/view.do" in lower:
        return "bbs_view"
    if "/portal/civil/list.do" in lower:
        return "civil_list"
    if "/portal/civil/view.do" in lower:
        return "civil_view"
    if "/portal/contents.do" in lower:
        return "contents"
    return "other"


def get_top_menu_name(url):
    mid = get_mid(url)
    if len(mid) >= 2:
        return ALLOWED_MID_PREFIXES.get(mid[:2], "기타")
    return "기타"

# =========================================================
# 탐색 범위 판별
# =========================================================
def is_portal_url(url):
    parsed = urlparse(url)
    return parsed.netloc in ALLOWED_DOMAINS and parsed.path.startswith("/portal/")


def has_allowed_mid(url):
    mid = get_mid(url)
    if mid in FORCE_ALLOW_MIDS:
        return True
    if not mid or len(mid) < 2:
        return False
    if mid[:2] not in ALLOWED_MID_PREFIXES:
        return False
    for prefix in EXCLUDE_MID_PREFIXES:
        if mid.startswith(prefix):
            return False
    return True

def extract_year_from_text(text):
    if not text:
        return None

    m = re.search(r"(20\d{2})", text)
    if m:
        return int(m.group(1))

    return None

# 제45회 (2024), 2024년, 2023 같은 연도별 메뉴 필터.
# anchor_text : HTML의 <a> 태그 안에 사용자에게 보이는 글씨
def is_recent_year_menu(anchor_text, url):
    text_year = extract_year_from_text(anchor_text)
    url_year = extract_year_from_text(url)

    year = text_year or url_year

    # 연도가 없는 일반 메뉴는 그대로 허용
    if year is None:
        return True

    return MIN_YEAR_MENU <= year <= CURRENT_YEAR

def is_allowed_url(url):
    lower = url.lower()
    if any(x in lower for x in DENY_URL_KEYWORDS):
        return False
    if not is_portal_url(url):
        return False
    if not any(x in lower for x in ALLOWED_PATH_KEYWORDS):
        return False
    return has_allowed_mid(url)


def should_save(url, anchor_text=""):
    page_type = classify_page_type(url)

    if not is_recent_year_menu(anchor_text, url):
        return False

    return page_type in ("contents", "bbs_view", "civil_view") and has_allowed_mid(url)

# =========================================================
# HTML 전처리 / 제목 / 메타데이터
# =========================================================
def remove_noise_nodes(soup):
    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()


def is_bad_title(title):
    if not title:
        return True
    title = title.strip()
    bad_titles = ["서브 메뉴", "메뉴", "주메뉴", "사이트맵", "검색", "공유", "프린트"]
    if title in bad_titles:
        return True
    if "Saha District Office" in title:
        return True
    return False


def extract_title(soup):
    if soup.title:
        raw = clean_inline(soup.title.get_text(" ", strip=True))
        parts = [clean_inline(p) for p in raw.split("|") if clean_inline(p)]
        if parts:
            candidate = parts[0]
            candidate = re.sub(r"\s*목록\s*$", "", candidate).strip()
            candidate = re.sub(r"\s*상세\s*$", "", candidate).strip()
            if 2 <= len(candidate) <= 120 and not is_bad_title(candidate):
                return candidate

    for selector in TITLE_SELECTORS:
        node = soup.select_one(selector)
        if node:
            candidate = clean_inline(node.get_text(" ", strip=True))
            candidate = re.sub(r"\s*목록\s*$", "", candidate).strip()
            candidate = re.sub(r"\s*상세\s*$", "", candidate).strip()
            if 2 <= len(candidate) <= 120 and not is_bad_title(candidate):
                return candidate
    return ""


def extract_metadata(soup):
    full_text = soup.get_text("\n", strip=True)

    department = ""
    date = ""
    views = None

    dept_patterns = [
        r"담당부서\s*[:：]?\s*([^\n|]+)",
        r"콘텐츠\s*관리부서\s*[:：]?\s*([^\n|]+)",
        r"작성자\s*[:：]?\s*([^\n|]+)",
    ]
    for pattern in dept_patterns:
        m = re.search(pattern, full_text)
        if m:
            department = clean_inline(m.group(1))
            break

    date_patterns = [
        r"최근업데이트\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"최종수정일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"등록일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"작성일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
        r"게시일\s*[:：]?\s*((?:20\d{2})[./-]\s*\d{1,2}[./-]\s*\d{1,2})",
    ]
    for pattern in date_patterns:
        m = re.search(pattern, full_text)
        if m:
            date = normalize_date(m.group(1))
            break

    view_patterns = [
        r"조회수\s*[:：]?\s*([\d,]+)",
        r"조회\s*[:：]?\s*([\d,]+)",
    ]
    for pattern in view_patterns:
        m = re.search(pattern, full_text)
        if m:
            views = normalize_views(m.group(1))
            break

    return {
        "department": department,
        "date": date,
        "views": views,
    }

# =========================================================
# 본문 영역 선택
# =========================================================
def score_node_text(text):
    score = 0
    for kw in SECTION_HINTS:
        if kw in text:
            score += 2
    score += min(len(text) // 250, 8)
    for kw in MENU_SIGNALS:
        if kw in text:
            score -= 2
    return score


def select_main_content(soup):
    candidates = []
    for selector in CONTENT_SELECTORS:
        for node in soup.select(selector):
            text = clean_text(node.get_text("\n", strip=True))
            if len(text) < 80:
                continue
            candidates.append((score_node_text(text), len(text), node))
    if not candidates:
        return soup.body
    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]


    noise_patterns = [
        r"^이전글.*", r"^다음글.*", r"^목록.*", r"^공유.*", r"^프린트.*",
        r"^저작권.*", r"^개인정보처리방침.*", r"^만족도 조사.*",
        r"^첨부파일.*뷰어다운로드.*", r"^주메뉴.*", r"^통합검색.*",
        r"^관련사이트.*", r"^콘텐츠 관리부서.*", r"^최종수정일.*",
    ]
    lines = []
    for line in text.split("\n"):
        line = clean_text(line)
        if not line:
            continue
        if any(re.match(p, line) for p in noise_patterns):
            continue
        if len(line) <= 1:
            continue
        lines.append(line)
    return "\n".join(lines).strip()

def remove_noise_lines(text):
    noise_exact = {
        "열기",
        "닫기",
        "블로그",
        "인스타그램",
        "페이스북",
        "카카오",
        "트위터",
        "유튜브",
        "인쇄하기",
        "프린트",
        "공유",
        "목록",
        "검색",
        "로그인",
        "로그아웃",
        "사이트맵",
        "저작권",
        "개인정보처리방침",
        "이전글",
        "다음글",
    }

    noise_patterns = [
        r"^이전글.*",
        r"^다음글.*",
        r"^만족도 조사.*",
        r"^콘텐츠 만족도.*",
        r"^저작권.*",
        r"^개인정보처리방침.*",
        r"^공유.*",
        r"^프린트.*",
        r"^인쇄하기.*",
        r"^SNS.*",
        r"^페이스북.*",
        r"^카카오.*",
        r"^인스타그램.*",
        r"^블로그.*",
        r"^유튜브.*",
        r"^열기.*",
        r"^닫기.*",
    ]

    lines = []

    for line in text.split("\n"):
        line = clean_inline(line)

        if not line:
            continue

        # 완전 일치 제거
        if line in noise_exact:
            continue

        # 패턴 제거
        matched = False

        for pattern in noise_patterns:
            if re.match(pattern, line):
                matched = True
                break

        if matched:
            continue

        # 너무 짧은 메뉴 제거
        if len(line) <= 1:
            continue

        lines.append(line)

    cleaned = "\n".join(lines).strip()

    # SNS 묶음 제거
    cleaned = re.sub(
        r"(열기\n)?블로그\n인스타그램\n페이스북\n카카오\n닫기(\n인쇄하기)?",
        "",
        cleaned,
        flags=re.MULTILINE
    ).strip()

    # 공백 정리
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)

    return cleaned

# =========================================================
# 섹션 구조 추출: h1/h2/h3/h4, table, ul, dl 반영
# =========================================================
def get_node_level(node):
    if not isinstance(node, Tag):
        return 0
    if node.name and re.fullmatch(r"h[1-6]", node.name):
        return int(node.name[1])
    if node.name == "dt":
        return 5
    if node.name == "strong":
        txt = clean_inline(node.get_text(" ", strip=True))
        if 2 <= len(txt) <= 40:
            return 5
    return 0


def table_to_text(table):
    rows = []
    headers = []
    thead = table.find("thead")
    if thead:
        headers = [clean_inline(th.get_text(" ", strip=True)) for th in thead.find_all(["th", "td"])]

    for tr in table.find_all("tr"):
        cells = [clean_inline(td.get_text(" ", strip=True)) for td in tr.find_all(["th", "td"])]
        cells = [c for c in cells if c]
        if not cells:
            continue
        if headers and len(headers) == len(cells):
            rows.append(" | ".join([f"{h}: {c}" for h, c in zip(headers, cells) if h and c]))
        else:
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def list_to_text(node):
    items = []

    for li in node.find_all("li", recursive=False):
        txt = clean_block_text(li.get_text("\n", strip=True))

        if not txt:
            continue

        lines = [line.strip() for line in txt.split("\n") if line.strip()]

        for line in lines:
            items.append(line)

    return "\n".join(items)


def dl_to_text(dl):
    items = []
    dts = dl.find_all("dt")
    dds = dl.find_all("dd")
    for dt, dd in zip(dts, dds):
        k = clean_inline(dt.get_text(" ", strip=True))
        v = clean_inline(dd.get_text(" ", strip=True))
        if k and v:
            items.append(f"{k}: {v}")
    return "\n".join(items)


def extract_structured_sections(main_node):
    """
    본문 순서를 유지하면서 h1/h2/h3/h4, 표, 목록을 섹션 단위로 저장한다.
    예)
    주민등록등·초본
      구비서류
        본인: 신분증
        위임을 받은 자: ...
    """
    sections = []
    heading_stack = []
    seen = set()

    def current_path():
        return [h["title"] for h in heading_stack]

    def push_heading(level, title):
        nonlocal heading_stack
        heading_stack = [h for h in heading_stack if h["level"] < level]
        heading_stack.append({"level": level, "title": title})

    for node in main_node.descendants:
        if not isinstance(node, Tag):
            continue

        level = get_node_level(node)
        if level:
            title = clean_inline(node.get_text(" ", strip=True))
            if title and len(title) <= 80:
                push_heading(level, title)
            continue

        block_text = ""
        block_type = "paragraph"

        if node.name == "table":
            block_text = table_to_text(node)
            block_type = "table"
        elif node.name in ("ul", "ol"):
            block_text = list_to_text(node)
            block_type = "list"
        elif node.name == "dl":
            block_text = dl_to_text(node)
            block_type = "definition_list"
        elif node.name in ("p", "div"):
            # div는 자식 table/list가 있으면 중복 방지
            if node.find(["table", "ul", "ol", "dl", "h1", "h2", "h3", "h4", "h5"]):
                continue
            block_text = clean_inline(node.get_text(" ", strip=True))
            block_type = "paragraph"
        else:
            continue

        block_text = clean_text(block_text)
        block_text = remove_noise_lines(block_text)

        if len(block_text) < 3:
            continue

        key = (tuple(current_path()), block_type, block_text[:200])
        if key in seen:
            continue
        seen.add(key)

        sections.append({
            "heading_path": current_path(),
            "block_type": block_type,
            "text": block_text,
        })

    return sections


def sections_to_text(title, menu_path, sections, shortcut_links):
    parts = []
    if title:
        parts.append(f"제목: {title}")
    if menu_path:
        parts.append("메뉴경로: " + " > ".join(menu_path))

    if sections:
        parts.append("[섹션 구조]")
        last_path = None
        for sec in sections:
            path = sec.get("heading_path", [])
            if path != last_path and path:
                parts.append(" > ".join(path))
                last_path = path
            label = sec.get("block_type", "paragraph")
            txt = sec.get("text", "")
            if label == "table":
                parts.append("[표]\n" + txt)
            elif label == "list":
                parts.append("[목록]")
                parts.append(txt)
            elif label == "definition_list":
                parts.append("[정의목록]\n" + txt)
            else:
                parts.append(txt)

    if shortcut_links:
        parts.append("[바로가기 링크]")
        for link in shortcut_links:
            parts.append(f"- {link['text']}: {link['url']}")

    text = clean_text("\n\n".join(parts))
    text = remove_noise_lines(text)

    return text


# 바로가기 / 링크 추출
def is_shortcut_text(text):
    text = clean_inline(text)
    keywords = ["바로가기", "신청하기", "예약하기", "조회하기", "다운로드", "홈페이지", "사이트", "민원24", "정부24"]
    return any(k in text for k in keywords)

def is_valid_shortcut_link(text, href, full_url):
    text = clean_inline(text)
    href = href or ""
    full_url = full_url or ""

    if not text:
        return False

    # SNS/페이지네이션/관리 버튼 제외
    if any(bad in text for bad in SHORTCUT_DENY_TEXTS):
        return False

    if href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return False

    # 실제 URL이 없으면 저장하지 않음
    if not full_url.startswith(("http://", "https://")):
        return False

    # 너무 일반적인 버튼명 제외
    if text in ["바로가기", "자세히보기", "자세히 보기"]:
        return False

    # 허용 키워드가 있으면 저장
    if any(good in text for good in SHORTCUT_ALLOW_TEXTS):
        return True

    # 새창으로 열리는 외부 행정 사이트는 저장
    parsed = urlparse(full_url)
    if parsed.netloc and parsed.netloc not in ALLOWED_DOMAINS:
        return True

    return False

def extract_shortcut_links(main_node, base_url):
    links = []

    if not main_node:
        return links

    for a in main_node.find_all("a", href=True):
        href = a.get("href", "").strip()
        raw_text = a.get_text(" ", strip=True)
        text = clean_inline(raw_text)

        # anchor text가 URL 자체면 주변 설명 텍스트 사용
        if re.fullmatch(r"https?://[^ ]+", text):
            parent = a.parent

            candidate = ""

            # 부모 li/td/div/p 안의 전체 텍스트 확인
            if parent:
                candidate = clean_inline(
                    parent.get_text(" ", strip=True)
                )

            # URL 제거 후 설명만 남기기
            candidate = re.sub(
                r"https?://\\S+",
                "",
                candidate
            ).strip()

            # 너무 짧지 않으면 교체
            if len(candidate) >= 2:
                text = candidate

        text = (
            text.replace("새창으로열림", "")
            .replace("새창", "")
            .strip()
        )
        # fallback
        if not text or re.fullmatch(r"https?://[^ ]+", text):
            parsed = urlparse(full_url)

            domain = parsed.netloc.lower()

            DOMAIN_NAME_HINTS = {
                "passport.go.kr": "여권안내 홈페이지",
                "gov.kr": "정부24",
                "korea.kr": "대한민국 정책브리핑",
            }

            for k, v in DOMAIN_NAME_HINTS.items():
                if k in domain:
                    text = v
                    break

        if href.startswith(("javascript:", "mailto:", "tel:", "#")):
            continue

        full_url = urljoin(base_url, href)
        full_url, _ = urldefrag(full_url)

        if not is_valid_shortcut_link(text, href, full_url):
            continue

        links.append({
            "text": text,
            "url": full_url,
            "raw_href": href,
        })

    dedup = {}
    for item in links:
        key = (item["text"], item["url"])
        dedup[key] = item

    return list(dedup.values())

# URL주소만 있는 목록 거르기
# source_url = 원본페이지, shorcut_url = 바로가기 링크
def make_shortcut_doc(
    source_url,
    link,
    menu_path,
    parent_title="",
    page_type="shortcut_link",
):
    text = clean_text(f"""
    제목: {link['text']}
    상위문서: {parent_title}
    메뉴경로: {' > '.join(menu_path)}
    분류: 바로가기 링크
    바로가기명: {link['text']}
    바로가기URL: {link['url']}
    원본페이지: {source_url}
    """)

    return {
        "doc_id": url_to_id(source_url + "|shortcut|" + link["text"] + "|" + link["url"]),
        "url": link["url"],
        "source_url": source_url,
        "page_type": page_type,
        "category": "바로가기",
        "title": link["text"],
        "parent_title": parent_title if page_type != "menu_shortcut" else "",
        "shortcut_name": link["text"],
        "menu_path": menu_path,
        "shortcut_url": link["url"],
        "raw_href": link.get("raw_href", ""),
        "text": text,
        "paragraphs": [text],
        "source": "saha.go.kr",
    }

# 새창/바로가기 링크는 하위 탐색 X, 대신 shortcut_link 문서로 JSONL 저장 O
def is_shortcut_only_link(a, href, text):
    href = href or ""
    text = clean_inline(text)

    if href.startswith(("javascript:", "mailto:", "tel:", "#")):
        return False

    full_url = urljoin("https://www.saha.go.kr", href)
    full_url, _ = urldefrag(full_url)

    return is_valid_shortcut_link(text, href, full_url)

def extract_links_from_raw_html(html, current_url, parent_menu_path=None):
    parent_menu_path = parent_menu_path or []

    soup = BeautifulSoup(html, "html.parser")

    links = []

    for a in soup.find_all("a", href=True):
        href = a.get("href", "").strip()

        anchor_text = clean_inline(
            a.get_text(" ", strip=True)
        )

        # 새창/바로가기 링크는 탐색하지 않음
        # (대신 shortcut_link 문서로 따로 저장)
        if is_shortcut_only_link(a, href, anchor_text):
            continue

        normalized = normalize_url(current_url, href)

        if not normalized:
            continue

        # 허용 범위 URL만 탐색
        if not is_allowed_url(normalized):
            continue

        # 연도별 메뉴는 최근 5년만 허용
        # 예: 제45회 (2024)
        if not is_recent_year_menu(anchor_text, normalized):
            continue

        menu_path = list(parent_menu_path)

        if (
            anchor_text
            and anchor_text not in menu_path
            and len(anchor_text) <= 60
        ):
            menu_path.append(anchor_text)

        links.append({
            "url": normalized,
            "parent_url": current_url,
            "anchor_text": anchor_text,
            "menu_path": menu_path,
        })

    # 중복 제거
    dedup = {}

    for item in links:
        url = item["url"]

        # 더 긴 menu_path 우선
        if (
            url not in dedup
            or len(item["menu_path"])
            > len(dedup[url]["menu_path"])
        ):
            dedup[url] = item

    return list(dedup.values())

# =========================================================
# 목록형 게시판 처리
# =========================================================
def extract_bbs_rows(list_html, list_url):
    soup = BeautifulSoup(list_html, "html.parser")
    rows = []

    for tr in soup.select("table tr"):
        cells = [clean_inline(td.get_text(" ", strip=True)) for td in tr.find_all(["th", "td"])]
        if len(cells) < 3:
            continue

        a = tr.find("a", href=True)
        if not a:
            continue

        view_url = normalize_url(list_url, a.get("href"))
        if not view_url:
            continue

        row_text = " | ".join(cells)
        date_match = re.search(r"(20\d{2})[./-](\d{1,2})[./-](\d{1,2})", row_text)
        row_date = ""
        if date_match:
            y, m, d = date_match.groups()
            row_date = f"{y}-{int(m):02d}-{int(d):02d}"

        # 일반적인 표 순서: 번호, 제목, 담당부서, 작성일, 조회
        title = clean_inline(a.get_text(" ", strip=True))
        number = cells[0] if cells else ""
        department = ""
        views = None

        for c in cells:
            if re.fullmatch(r"\d[\d,]*", c):
                views = normalize_views(c)

        # 담당부서는 날짜 앞뒤 셀에서 추정
        if row_date:
            for i, c in enumerate(cells):
                if row_date.replace("-", ".") in c or row_date in c:
                    if i > 0:
                        department = cells[i - 1]
                    break

        rows.append({
            "number": number,
            "title": title,
            "department": department,
            "date": row_date,
            "views": views,
            "url": view_url,
        })

    return rows


def get_bbs_page_url(list_url, page):
    if page == 1:
        return list_url
    sep = "&" if "?" in list_url else "?"
    return f"{list_url}{sep}page={page}"


def is_recent_row(row):
    dt = parse_date(row.get("date", ""))
    if not dt:
        return True
    return dt >= RECENT_CUTOFF

# =========================================================
# 문서 추출
# =========================================================
def split_paragraphs(text):
    return [clean_text(p) for p in re.split(r"\n{2,}", text) if len(clean_text(p)) >= 20]


def extract_document(html, url, menu_path=None):
    soup = BeautifulSoup(html, "html.parser")
    remove_noise_nodes(soup)

    title = extract_title(soup)
    main_node = select_main_content(soup)
    if not main_node:
        return title, "", [], [], []

    sections = extract_structured_sections(main_node)
    shortcut_links = extract_shortcut_links(main_node, url)
    text = sections_to_text(title, menu_path, sections, shortcut_links)
    text = remove_noise_lines(text)
    paragraphs = split_paragraphs(text)

    return title, text, paragraphs, sections, shortcut_links


def is_menu_like_text(text):
    hit = sum(1 for x in MENU_SIGNALS if x in text)
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return True
    short_count = sum(1 for line in lines if len(line) <= 12)
    return hit >= 3 or (short_count / len(lines)) > 0.70


def document_score(url, title, text, sections):
    score = 0
    page_type = classify_page_type(url)
    if page_type in ("bbs_view", "civil_view"):
        score += 4
    elif page_type == "contents":
        score += 2

    if 2 <= len(title) <= 120:
        score += 1
    if len(text) >= 200:
        score += 2
    if len(text) >= 500:
        score += 2
    if sections:
        score += min(len(sections), 5)
    if any(kw in text for kw in SECTION_HINTS):
        score += 3
    if is_menu_like_text(text):
        score -= 5
    return score

# =========================================================
# 저장 문서 생성
# =========================================================
def make_doc(url, parent_url, anchor_text, menu_path, html, extra_meta=None):
    title, text, paragraphs, sections, shortcut_links = extract_document(html, url, menu_path)
    soup_meta = BeautifulSoup(html, "html.parser")
    metadata = extract_metadata(soup_meta)

    extra_meta = extra_meta or {}
    page_type = classify_page_type(url)

    doc = {
        "doc_id": url_to_id(url),
        "url": url,
        "parent_url": parent_url,
        "anchor_text": anchor_text,
        "menu_path": menu_path,
        "top_menu": get_top_menu_name(url),
        "page_type": page_type,
        "title": extra_meta.get("title") or title,
        "department": extra_meta.get("department") or metadata.get("department", ""),
        "date": extra_meta.get("date") or metadata.get("date", ""),
        "views": extra_meta.get("views") if extra_meta.get("views") is not None else metadata.get("views"),
        "sections": sections,
        "shortcut_links": shortcut_links,
        "text": text,
        "paragraphs": paragraphs,
        "source": "saha.go.kr",
    }

    if extra_meta:
        doc.update({k: v for k, v in extra_meta.items() if v not in (None, "")})

    return doc

# =========================================================
# 크롤링 메인
# =========================================================
def crawl():
    ensure_dir(OUTPUT_DIR)

    session = requests.Session()
    session.headers.update(HEADERS)

    visited = set()
    queued = set()
    queue = deque()
    START_URL_SET = {item["url"] for item in START_URLS}
    saved_doc_ids = set()
    saved_count = 0
    saved_shortcut_urls = set()

    for seed in START_URLS:
        url = seed["url"]
        queue.append({
            "url": url,
            "parent_url": "",
            "anchor_text": seed["menu_path"][-1],
            "menu_path": seed["menu_path"],
        })
        queued.add(url)

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as out:
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
            # 메뉴의 새창 바로가기 → 전체 soup에서 추출
            soup_for_shortcut = BeautifulSoup(html, "html.parser")

            shortcut_links = []

            # 1. 본문 안 바로가기만 추출
            soup_for_main_shortcut = BeautifulSoup(html, "html.parser")
            remove_noise_nodes(soup_for_main_shortcut)
            main_node_for_shortcut = select_main_content(soup_for_main_shortcut)

            shortcut_links.extend(
                extract_shortcut_links(main_node_for_shortcut, url)
            )

            # 2. 메뉴 영역의 '새창으로열림' 링크는 시작 메뉴 페이지에서만 추출
            # 예: 정보공개 > 사하알림 페이지
            if url in START_URL_SET:
                soup_for_menu_shortcut = BeautifulSoup(html, "html.parser")

                for a in soup_for_menu_shortcut.find_all("a", href=True):
                    raw_text = a.get_text(" ", strip=True)
                    text = clean_inline(raw_text)
                    href = a.get("href", "").strip()

                    if "새창" not in text and a.get("target") != "_blank":
                        continue

                    text = (
                        text.replace("새창으로열림", "")
                        .replace("새창", "")
                        .strip()
                    )

                    if not text:
                        continue

                    # 저장하고 싶은 대표 새창 메뉴만 허용
                    if text not in ["계약정보공개", "재정정보공개"]:
                        continue

                    full_url = urljoin(url, href)
                    full_url, _ = urldefrag(full_url)

                    shortcut_links.append({
                        "text": text,
                        "url": full_url,
                        "raw_href": href,
                    })

            page_type = classify_page_type(url)
            # 중복 제거
            shortcut_dedup = {}
            for link in shortcut_links:
                key = (
                    link.get("text", ""),
                    link.get("url", ""),
                    link.get("raw_href", ""),
                )
                shortcut_dedup[key] = link

            shortcut_links = list(shortcut_dedup.values())

            for shortcut in shortcut_links:
                if not shortcut.get("url"):
                    continue

                page_title = extract_title(BeautifulSoup(html, "html.parser"))

                shortcut_doc = make_shortcut_doc(
                    url,
                    shortcut,
                    menu_path,
                    parent_title="",
                    page_type="menu_shortcut",
                )

                shortcut_key = shortcut_doc.get("shortcut_url", "")

                if shortcut_key not in saved_shortcut_urls:
                    out.write(json.dumps(shortcut_doc, ensure_ascii=False) + "\n")
                    out.flush()

                    saved_shortcut_urls.add(shortcut_key)

                    saved_doc_ids.add(shortcut_doc["doc_id"])

                    saved_count += 1

                    print(
                        f"  바로가기 저장 완료 ({saved_count}): "
                        f"{shortcut_doc['title']}"
                    )
            

            # 링크 수집: contents든 list든 직접 클릭 메뉴까지 계속 탐색
            links = extract_links_from_raw_html(html, url, parent_menu_path=menu_path)

            # 목록형 게시판이면 최근 1년 상세글을 직접 방문해서 저장
            if page_type == "bbs_list":
                print("  목록형 게시판 처리")
                for page in range(1, MAX_BOARD_PAGES_PER_LIST + 1):
                    list_page_url = get_bbs_page_url(url, page)
                    try:
                        r = session.get(list_page_url, timeout=TIMEOUT)
                        r.raise_for_status()
                    except Exception as e:
                        print(f"    목록 page={page} 요청 실패: {e}")
                        continue

                    rows = extract_bbs_rows(r.text, list_page_url)
                    if not rows:
                        if page == 1:
                            print("    게시글 행 없음")
                        break

                    old_count = 0
                    for row in rows:
                        if not is_recent_row(row):
                            old_count += 1
                            continue

                        view_url = row["url"]
                        if view_url in visited:
                            continue
                        visited.add(view_url)

                        print(f"    [BBS VIEW] {row.get('title', '')} / {view_url}")
                        try:
                            vr = session.get(view_url, timeout=TIMEOUT)
                            vr.raise_for_status()
                        except Exception as e:
                            print(f"      상세 요청 실패: {e}")
                            continue

                        extra_meta = {
                            "board_number": row.get("number", ""),
                            "title": row.get("title", ""),
                            "department": row.get("department", ""),
                            "date": row.get("date", ""),
                            "views": row.get("views"),
                        }
                        doc = make_doc(
                            view_url,
                            parent_url=url,
                            anchor_text=row.get("title", ""),
                            menu_path=menu_path + [row.get("title", "")],
                            html=vr.text,
                            extra_meta=extra_meta,
                        )

                        if len(doc.get("text", "")) >= 80:
                            doc_id = doc["doc_id"]
                            if doc_id not in saved_doc_ids:
                                out.write(json.dumps(doc, ensure_ascii=False) + "\n")
                                out.flush()
                                saved_doc_ids.add(doc_id)
                                saved_count += 1
                                print(f"      저장 완료 ({saved_count}): {doc['title']}")

                        time.sleep(REQUEST_DELAY)

                    if old_count >= len(rows):
                        print("    최근 1년 이전 게시글만 있어 목록 중단")
                        break

                    time.sleep(REQUEST_DELAY)

            elif should_save(url, anchor_text):
                try:
                    doc = make_doc(url, parent_url, anchor_text, menu_path, html)
                    score = document_score(url, doc["title"], doc["text"], doc["sections"])

                    print(f"  제목: {doc['title']}")
                    print(f"  본문 길이: {len(doc['text'])}")
                    print(f"  섹션 수: {len(doc['sections'])}")
                    print(f"  바로가기 수: {len(doc['shortcut_links'])}")
                    print(f"  문서 점수: {score}")

                    if doc.get("text") and len(doc["text"]) >= 80 and score >= 0:
                        doc_id = doc["doc_id"]
                        if doc_id not in saved_doc_ids:
                            out.write(json.dumps(doc, ensure_ascii=False) + "\n")
                            out.flush()
                            saved_doc_ids.add(doc_id)
                            saved_count += 1
                            print(f"  저장 완료 ({saved_count}): {doc['title']}")
                    else:
                        print("  저장 안 함: 본문 부족 또는 메뉴성 페이지")

                except Exception as e:
                    print(f"  파싱 실패: {e}")
            else:
                print("  저장 안 함: 목록/허브 또는 범위 외 페이지")

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
