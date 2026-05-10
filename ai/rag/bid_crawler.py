import os
import re
import json
import time
import hashlib
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

EMINWON_BASE_URL = "https://eminwon.saha.go.kr"

START_URL = "https://www.saha.go.kr/portal/contents.do?mId=0301040000"

LIST_URL = "https://eminwon.saha.go.kr/emwp/jsp/ofr/OfrNotAncmtLSub.jsp?not_ancmt_se_code=02"

ACTION_URL = (
    "https://eminwon.saha.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do"
)

OUTPUT_DIR = "data/raw"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "saha_bid_docs.jsonl")

MAX_LIST_PAGES = 5
REQUEST_DELAY = 0.7
TIMEOUT = 15

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": START_URL,
}

DEFAULT_DEPARTMENT = "재무과"

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


def make_id(url):
    return hashlib.md5(url.encode("utf-8")).hexdigest()


def fetch(session, url):
    response = session.get(url, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def fetch_list_page(session, page):
    data = {
        "pageIndex": str(page),
        "jndinm": "OfrNotAncmtEJB",
        "context": "NTIS",
        "method": "selectListOfrNotAncmt",
        "methodnm": "selectListOfrNotAncmtHomepage",
        "not_ancmt_mgt_no": "",
        "homepage_pbs_yn": "Y",
        "subCheck": "Y",
        "ofr_pageSize": "10",
        "not_ancmt_se_code": "02",
        "title": "입찰공고",
        "cha_dep_code_nm": "",
        "initValue": "",
        "countYn": "Y",
        "list_gubun": "",
        "not_ancmt_sj": "",
        "not_ancmt_cn": "",
        "dept_nm": "",
        "is_mobile": "",
        "Key": "B_Subject",
        "temp": "",
    }

    response = session.post(
        ACTION_URL,
        data=data,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    response.raise_for_status()
    response.encoding = response.apparent_encoding

    return response.text


def fetch_detail_page(session, notice_id, page=1):
    data = {
        "pageIndex": str(page),
        "jndinm": "OfrNotAncmtEJB",
        "context": "NTIS",
        "method": "selectOfrNotAncmt",
        "methodnm": "selectOfrNotAncmtRegst",
        "not_ancmt_mgt_no": notice_id,
        "homepage_pbs_yn": "Y",
        "subCheck": "Y",
        "ofr_pageSize": "10",
        "not_ancmt_se_code": "02",
        "title": "입찰공고",
        "cha_dep_code_nm": "",
        "initValue": "",
        "countYn": "Y",
        "list_gubun": "",
        "not_ancmt_sj": "",
        "not_ancmt_cn": "",
        "dept_nm": "",
        "is_mobile": "",
        "Key": "B_Subject",
        "temp": "",
    }

    response = session.post(
        ACTION_URL,
        data=data,
        headers=HEADERS,
        timeout=TIMEOUT,
    )

    response.raise_for_status()
    response.encoding = response.apparent_encoding

    return response.text


def remove_noise(soup):
    for tag in soup(["script", "style", "noscript", "iframe", "svg"]):
        tag.decompose()


def extract_bid_list_url(html, base_url):
    soup = BeautifulSoup(html, "html.parser")

    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        text = clean_inline(a.get_text(" ", strip=True))

        if "OfrNotAncmtLSub.jsp" in href or "입찰정보" in text:
            return urljoin(base_url, href)

    return ""


def extract_detail_links(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []

    # 1) a 태그의 href / onclick 둘 다 확인
    for a in soup.find_all("a"):
        text = clean_inline(a.get_text(" ", strip=True))
        href = a.get("href", "") or ""
        onclick = a.get("onclick", "") or ""

        target = href + " " + onclick

        m = re.search(r"searchDetail\(['\"]?([^'\")]+)['\"]?\)", target)
        if not m:
            continue

        notice_id = m.group(1)

        links.append({
            "notice_id": notice_id,
            "anchor_text": text,
        })

    # 2) HTML 전체에서 searchDetail('...') 직접 찾기
    for notice_id in re.findall(r"searchDetail\(['\"]?([^'\")]+)['\"]?\)", html):
        links.append({
            "notice_id": notice_id,
            "anchor_text": "",
        })

    # 중복 제거
    dedup = {}

    for item in links:
        notice_id = item["notice_id"]

        # 숫자 ID만 허용
        if not notice_id.isdigit():
            continue

        dedup[notice_id] = item

    return list(dedup.values())


def extract_field(text, field_names):
    for field in field_names:
        pattern = rf"{re.escape(field)}\s*[:：]?\s*([^\n]+)"
        m = re.search(pattern, text)

        if m:
            return clean_inline(m.group(1))

    return ""

def extract_attachments(soup):
    attachments = []

    for a in soup.find_all("a", href=True):
        file_name = clean_inline(a.get_text(" ", strip=True))
        href = a.get("href", "").strip()

        if not file_name:
            continue

        if not re.search(r"\.(hwp|hwpx|pdf|doc|docx|xls|xlsx|zip)$", file_name, re.I):
            continue

        file_url = ""

        # 실제 다운로드 경로일 때만 URL 생성
        if href.startswith("http"):
            file_url = href

        elif href.startswith("/emwp/"):
            file_url = urljoin(EMINWON_BASE_URL, href)

        elif href.startswith("../") or href.startswith("./"):
            file_url = urljoin(ACTION_URL, href)

        # javascript면 원문만 보관하고 URL은 비워둠
        elif href.startswith("javascript:"):
            file_url = ""

        # 빈 href, #, 기타 이상한 값은 URL 생성하지 않음
        else:
            file_url = ""

        attachments.append({
            "file_name": file_name,
            "file_url": file_url,
            "raw_href": href,
        })

    return attachments


def extract_detail_page(url, html, notice_id):
    soup = BeautifulSoup(html, "html.parser")
    remove_noise(soup)

    full_text = clean_text(
        soup.get_text("\n", strip=True)
    )

    title = extract_field(full_text, ["제목"])

    notice_type = extract_field(
        full_text,
        ["고시공고구분"]
    )

    notice_no = extract_field(
        full_text,
        ["고시공고번호"]
    )

    date = extract_field(
        full_text,
        ["작성일"]
    )

    department = extract_field(
        full_text,
        ["담당부서"]
    )

    phone = extract_field(
        full_text,
        ["담당자 연락처", "전화번호", "연락처"]
    )

    attachments = extract_attachments(soup)

    body = full_text

    start_candidates = [
        "1. 공고대상",
        "1. 입찰에 부치는 사항",
        "1. 공고기간",
        "1. 견적에 부치는 사항",
        "가. 입찰건명",
    ]

    for marker in start_candidates:
        idx = full_text.find(marker)

        if idx != -1:
            body = full_text[idx:]
            break

    for stop in ["목록", "만족도조사", "Quick Menu"]:
        idx = body.find(stop)

        if idx != -1:
            body = body[:idx]

    body = clean_text(body)

    if not title:
        title = "입찰공고"

    if not department:
        department = DEFAULT_DEPARTMENT

    attachment_text = "\n".join([
        f"- {item['file_name']} ({item['file_url']})"
        for item in attachments
    ])

    text = clean_text(f"""
제목: {title}
메뉴경로: 정보공개 > 사하알림 > 입찰정보
분류: 입찰정보
고시공고구분: {notice_type}
고시공고번호: {notice_no}
작성일: {date}
담당부서: {department}
담당자 연락처: {phone}
상세URL: {url}

첨부파일:
{attachment_text}

[본문]
{body}
""")

    paragraphs = [
        p
        for p in re.split(r"\n{2,}", text)
        if clean_inline(p)
    ]

# 사이트 구조상 공고별 “바로가기 URL”은 없고, POST로 상세를 여는 방식(예전 전자정부 스타일 JSP 시스템)
    return {
    "doc_id": make_id(f"{START_URL}#notice-{notice_id}"),
    "url": f"{START_URL}#notice-{notice_id}",
    "display_url": START_URL,
    "source_url": START_URL,
    "list_url": LIST_URL,
    "notice_id": notice_id,
    "detail_key": f"not_ancmt_mgt_no={notice_id}",
    "page_type": "bid_notice",
    "category": "입찰정보",
    "title": title,
    "notice_type": notice_type,
    "notice_no": notice_no,
    "date": date,
    "department": department,
    "phone": phone,
    "attachments": attachments,
    "body": body,
    "menu_path": [
        "정보공개",
        "사하알림",
        "입찰정보",
    ],
    "text": text,
    "paragraphs": paragraphs,
    "source": "eminwon.saha.go.kr",
    }


def crawl_bid_pages():
    ensure_dir(OUTPUT_DIR)

    session = requests.Session()
    saved = 0
    visited_notice_ids = set()

    start_html = fetch(session, START_URL)

    list_url = extract_bid_list_url(
        start_html,
        START_URL,
    )

    print("입찰정보 목록 URL:", list_url)

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        for page in range(1, MAX_LIST_PAGES + 1):
            print(f"[LIST] page={page}")

            try:
                list_html = fetch_list_page(session, page)
                '''
                # 디버그용
                debug_path = (
                    f"data/raw/bid_list_debug_page_{page}.html"
                )
                with open(debug_path,"w",encoding="utf-8") as f:
                    f.write(list_html)
                '''

            except Exception as e:
                print(f"  목록 요청 실패: {e}")
                continue

            detail_links = extract_detail_links(list_html)

            print(f"  상세 링크 수: {len(detail_links)}")
            # 디버그
            print("searchDetail 개수:", list_html.count("searchDetail"))
            print("총 글 개수 문구 포함 여부:", "총 <strong>0</strong>개의 글" in list_html)

            if not detail_links:
                print("  상세 링크 없음")
                continue

            for link in detail_links:
                notice_id = link["notice_id"]

                if notice_id in visited_notice_ids:
                    continue

                visited_notice_ids.add(notice_id)

                print(f"  [DETAIL] {notice_id}")

                try:
                    detail_html = fetch_detail_page(
                        session,
                        notice_id,
                        page,
                    )

                    doc = extract_detail_page(
                        START_URL,
                        detail_html,
                        notice_id,
                    )

                    doc["notice_id"] = notice_id
                    doc["source_url"] = START_URL
                    doc["list_url"] = LIST_URL

                except Exception as e:
                    print(f"    상세 요청 실패: {e}")
                    continue

                if len(doc.get("text", "")) < 80:
                    print("    저장 안 함: 본문 부족")
                    continue

                out.write(
                    json.dumps(
                        doc,
                        ensure_ascii=False,
                    ) + "\n"
                )

                out.flush()

                saved += 1

                print(
                    f"    저장 완료 ({saved}): "
                    f"{doc['title']}"
                )

                time.sleep(REQUEST_DELAY)

            time.sleep(REQUEST_DELAY)

    print("\n입찰정보 크롤링 완료")
    print(f"- 저장 문서 수: {saved}")
    print(f"- 저장 파일: {OUTPUT_FILE}")


if __name__ == "__main__":
    crawl_bid_pages()