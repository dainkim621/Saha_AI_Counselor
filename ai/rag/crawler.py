import os
import re
import json
import time
import hashlib
from collections import deque
from urllib.parse import urljoin, urlparse, urldefrag

import requests
from bs4 import BeautifulSoup

# ==============================
# 설정
# ==============================
START_URLS = [
    # 허브 페이지: 저장은 안 하지만 상세 링크를 타기 위한 시작점
    "https://www.saha.go.kr/main.do",
    "https://www.saha.go.kr/portal/contents.do?mId=0102010000",
]

ALLOWED_DOMAINS = {"www.saha.go.kr", "m.saha.go.kr"}

OUTPUT_DIR = "data/raw"
OUTPUT_JSONL = os.path.join(OUTPUT_DIR, "saha_docs.jsonl")

MAX_PAGES = 80
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
    "bbs/list.do",
    "board/list.do",
    "board/view.do",
    "photo",
    "gallery",
    "youtube",
    "blog",
    "facebook",
    "instagram",
    "twitter",
]

# contents.do 상세 페이지 위주 저장
ALLOW_SAVE_KEYWORDS = [
    "contents.do",
]

# 링크 탐색 허용 범위
ALLOW_VISIT_KEYWORDS = [
    "contents.do",
    "/main.do",
]

# HTML 블록 단위 제거
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

TITLE_SELECTORS = [
    "h1",
    "h2",
    ".tit",
    ".title",
    ".subTitle",
    ".contTitle",
    ".pageTitle",
    ".subject",
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

PRIORITY_KEYWORDS = [
    "전입", "전입신고", "민원", "주민등록", "등본", "초본", "정부24",
    "무인민원", "발급", "신청", "서류", "수수료", "복지", "쓰레기", "배출",
    "구비서류", "처리기간", "신고기한", "문의처", "신청방법", "방문", "온라인"
]

STRONG_CIVIL_KEYWORDS = [
    "전입신고", "주민등록", "민원", "신청", "구비서류",
    "처리기간", "수수료", "문의처", "신고기한", "신청방법",
    "방문", "온라인", "처리절차", "제출서류"
]

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

SECTION_HINTS = [
    "신청대상", "신청방법", "처리절차", "처리기간", "수수료",
    "구비서류", "제출서류", "유의사항", "문의처", "신고기한",
    "온라인 신청", "방문 신청"
]


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


def should_visit(url: str) -> bool:
    lower_url = url.lower()

    if any(x in lower_url for x in DENY_URL_KEYWORDS):
        return False

    if not any(x in lower_url for x in ALLOW_VISIT_KEYWORDS):
        return False

    return True


def should_save(url: str) -> bool:
    lower_url = url.lower()

    if lower_url.endswith("/main.do"):
        return False

    return any(x in lower_url for x in ALLOW_SAVE_KEYWORDS)


def url_to_id(url: str) -> str:
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def is_html_response(response: requests.Response) -> bool:
    content_type = response.headers.get("Content-Type", "")
    return "text/html" in content_type.lower()


# ==============================
# 링크 수집
# ==============================
def extract_links_from_raw_html(html: str, current_url: str):
    """
    링크는 원본 HTML에서 먼저 수집
    """
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        normalized = normalize_url(current_url, a["href"])
        if normalized and should_visit(normalized):
            links.add(normalized)

    return sorted(links)


# ==============================
# 본문 추출
# ==============================
def remove_noise_nodes(soup: BeautifulSoup):
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()

    for selector in NOISE_SELECTORS:
        for node in soup.select(selector):
            node.decompose()


def extract_title(soup: BeautifulSoup) -> str:
    for selector in TITLE_SELECTORS:
        node = soup.select_one(selector)
        if node:
            txt = clean_text(node.get_text(" ", strip=True))
            if 2 <= len(txt) <= 120:
                return txt

    if soup.title:
        return clean_text(soup.title.get_text(" ", strip=True))

    return ""


def score_node_text(text: str) -> int:
    score = 0

    for kw in PRIORITY_KEYWORDS:
        if kw in text:
            score += 3

    for kw in SECTION_HINTS:
        if kw in text:
            score += 2

    for kw in BAD_TEXT_SIGNALS:
        if kw in text:
            score -= 2

    score += min(len(text) // 200, 10)
    return score


def select_main_content(soup: BeautifulSoup):
    candidates = []

    for selector in CONTENT_SELECTORS:
        for node in soup.select(selector):
            text = clean_text(node.get_text("\n", strip=True))
            if len(text) < 120:
                continue

            score = score_node_text(text)
            candidates.append((score, len(text), node))

    if not candidates:
        return None

    candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return candidates[0][2]


def remove_noise_lines(text: str) -> str:
    lines = []

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

        if len(line) <= 2:
            continue

        lines.append(line)

    return "\n".join(lines).strip()


def split_paragraphs(text: str):
    parts = re.split(r"\n{2,}", text)
    results = []

    for part in parts:
        part = clean_text(part)
        if len(part) >= 40:
            results.append(part)

    return results


def is_menu_like_text(text: str) -> bool:
    hit = sum(1 for x in MENU_SIGNALS if x in text)

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    line_count = len(lines)
    short_line_count = sum(1 for line in lines if len(line) <= 12)

    if hit >= 2:
        return True

    if line_count > 0 and (short_line_count / line_count) > 0.45:
        return True

    return False


def is_meaningful_text(title: str, text: str) -> bool:
    if not text or len(text) < 200:
        return False

    if is_menu_like_text(text):
        return False

    merged = f"{title}\n{text}"

    hit_count = sum(1 for kw in STRONG_CIVIL_KEYWORDS if kw in merged)
    structure_hit = sum(1 for kw in SECTION_HINTS if kw in merged)

    if hit_count >= 2:
        return True

    if hit_count >= 1 and structure_hit >= 2:
        return True

    return False


def build_structured_text(title: str, raw_text: str) -> str:
    """
    제목과 본문을 합쳐서 임베딩 검색에 더 잘 걸리도록 구성
    """
    text = raw_text.strip()

    if title and title not in text[:200]:
        text = f"{title}\n\n{text}"

    return clean_text(text)


def extract_text(html: str):
    soup = BeautifulSoup(html, "html.parser")
    remove_noise_nodes(soup)

    title = extract_title(soup)
    main_node = select_main_content(soup)

    if main_node is None:
        return title, "", []

    raw_text = clean_text(main_node.get_text("\n", strip=True))
    raw_text = remove_noise_lines(raw_text)
    raw_text = build_structured_text(title, raw_text)

    paragraphs = split_paragraphs(raw_text)
    return title, raw_text, paragraphs


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
        if url not in queued:
            queue.append(url)
            queued.add(url)

    saved_count = 0

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        while queue and len(visited) < MAX_PAGES:
            url = queue.popleft()
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

            # 1) 링크는 원본 HTML에서 수집
            links = extract_links_from_raw_html(html, url)

            # 2) main.do는 저장 금지, 링크만 추적
            if not should_save(url):
                print("  저장 안 함: main.do 또는 저장 대상 아님")
            else:
                try:
                    title, raw_text, paragraphs = extract_text(html)
                except Exception as e:
                    print(f"  파싱 실패: {e}")
                    raw_text, paragraphs, title = "", [], ""

                if raw_text and paragraphs and is_meaningful_text(title, raw_text):
                    doc = {
                        "doc_id": url_to_id(url),
                        "url": url,
                        "title": title,
                        "text": raw_text,
                        "paragraphs": paragraphs,
                        "source": "saha.go.kr",
                    }
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    saved_count += 1
                    print(f"  저장 완료 ({saved_count}): {title[:80] if title else '제목없음'}")
                else:
                    print("  저장 안 함: 본문 부족 또는 메뉴성 페이지")

            added = 0
            for link in links:
                if link not in visited and link not in queued:
                    queue.append(link)
                    queued.add(link)
                    added += 1

            print(f"  링크 추가: {added}개")
            time.sleep(REQUEST_DELAY)

    print("\n크롤링 완료")
    print(f"- 방문 페이지 수: {len(visited)}")
    print(f"- 저장 문서 수: {saved_count}")
    print(f"- 출력 파일: {OUTPUT_JSONL}")


if __name__ == "__main__":
    crawl()