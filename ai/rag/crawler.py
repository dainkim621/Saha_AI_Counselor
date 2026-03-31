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

MAX_PAGES = 30   # 테스트용
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
]

# contents.do 상세 페이지 위주
ALLOW_SAVE_KEYWORDS = [
    "contents.do",
]

# 링크 탐색은 조금 넓게 허용
ALLOW_VISIT_KEYWORDS = [
    "contents.do",
    "/main.do",
]

NOISE_SELECTORS = [
    "header", "footer", "nav", "aside",
    "#header", "#footer", "#gnb", "#lnb", "#snb",
    ".header", ".footer", ".gnb", ".lnb", ".snb",
    ".skip", ".breadcrumbs", ".location", ".quick",
    ".quickMenu", "#quickMenu", ".subMenu", ".menuArea",
    ".snsArea", ".shareArea", ".printArea",
]

TITLE_SELECTORS = [
    "h1", "h2", ".tit", ".title", ".subTitle", ".contTitle", ".pageTitle"
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
    "main",
    "article",
]

PRIORITY_KEYWORDS = [
    "전입", "전입신고", "민원", "주민등록", "등본", "초본", "정부24",
    "무인민원", "발급", "신청", "서류", "수수료", "복지", "쓰레기", "배출"
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

    return any(x in lower_url for x in ALLOW_VISIT_KEYWORDS)


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


def select_main_content(soup: BeautifulSoup):
    best_node = None
    best_len = 0

    for selector in CONTENT_SELECTORS:
        node = soup.select_one(selector)
        if not node:
            continue

        text_len = len(clean_text(node.get_text("\n", strip=True)))
        if text_len > best_len:
            best_len = text_len
            best_node = node

    return best_node


def split_paragraphs(text: str):
    parts = re.split(r"\n{2,}", text)
    results = []

    for part in parts:
        part = clean_text(part)
        if len(part) >= 40:
            results.append(part)

    return results


def is_menu_like_text(text: str) -> bool:
    menu_signals = [
        "비주얼 홍보 이미지", "이전 이미지", "다음 이미지", "퀵아이콘",
        "우리동 소식", "등록된 게시물이 없습니다", "사하구 홈페이지",
        "전자민원", "정보공개", "분야별 정보", "주메뉴"
    ]
    hit = sum(1 for x in menu_signals if x in text)
    return hit >= 2 and len(text) < 3000


def is_meaningful_text(title: str, text: str) -> bool:
    if not text or len(text) < 150:
        return False

    if is_menu_like_text(text):
        return False

    merged = f"{title}\n{text}"
    hit_count = sum(1 for kw in PRIORITY_KEYWORDS if kw in merged)

    if hit_count >= 1:
        return True

    if len(text) >= 800:
        return True

    return False


def extract_text(html: str):
    soup = BeautifulSoup(html, "html.parser")
    remove_noise_nodes(soup)

    title = extract_title(soup)
    main_node = select_main_content(soup)

    if main_node is None:
        return title, "", []

    raw_text = clean_text(main_node.get_text("\n", strip=True))
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