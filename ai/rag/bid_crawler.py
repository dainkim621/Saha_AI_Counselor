import os
import re
import json
import time
import hashlib
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

### 입찰정보 ###
EMINWON_BASE_URL = "https://eminwon.saha.go.kr"

START_URL = "https://www.saha.go.kr/portal/contents.do?mId=0301040000"

LIST_URL = "https://eminwon.saha.go.kr/emwp/jsp/ofr/OfrNotAncmtLSub.jsp?not_ancmt_se_code=02"

ACTION_URL = (
    "https://eminwon.saha.go.kr/emwp/gov/mogaha/ntis/web/ofr/action/OfrAction.do"
)

OUTPUT_DIR = "data/raw"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "saha_bid_docs.jsonl")

DELTA_DIR = os.path.join(OUTPUT_DIR, "delta")
HISTORY_DIR = os.path.join(OUTPUT_DIR, "history")
# 오늘 수정된 파일 저장용
OUTPUT_DELTA_FILE = os.path.join(DELTA_DIR, "saha_bid_docs_delta.jsonl")
# 변경 이력 누적 기록
OUTPUT_CHANGE_HISTORY_FILE = os.path.join(HISTORY_DIR, "bid_change_history.jsonl")
# 변경 감지 기록 
STATE_FILE = "data/state/bid_crawl_state.json"

MAX_LIST_PAGES = 1  # 매일 최대 10개의 정보 확인 
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

# 현재년도 확인 함수
def is_current_year_bid(date_text):
    if not date_text:
        return False

    current_year = time.strftime("%Y")

    match = re.search(r"\b(20\d{2})\b", str(date_text))

    if not match:
        return False

    return match.group(1) == current_year

def make_id(url):
    return hashlib.md5(url.encode("utf-8")).hexdigest()

# 변경 감지
def load_json_file(path):
    if not os.path.exists(path):
        return {}

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return {}
            return json.loads(content)
    except json.JSONDecodeError:
        print(f"{path} 파싱 실패 → 빈 상태로 시작")
        return {}


def save_json_file(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_existing_docs(path):
    docs = {}

    if not os.path.exists(path):
        return docs

    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                doc = json.loads(line)
            except json.JSONDecodeError:
                continue

            doc_id = doc.get("doc_id")
            if doc_id:
                docs[doc_id] = doc

    print(f"[LOAD EXISTING BID DOCS] {len(docs)}개 읽음")
    return docs


def save_existing_docs(path, docs):
    os.makedirs(os.path.dirname(path), exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        for doc in docs.values():
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")


def make_content_hash(doc):
    compare_data = {
        "notice_id": doc.get("notice_id", ""),
        "title": doc.get("title", ""),
        "notice_type": doc.get("notice_type", ""),
        "notice_no": doc.get("notice_no", ""),
        "date": doc.get("date", ""),
        "department": doc.get("department", ""),
        "phone": doc.get("phone", ""),
        "body": doc.get("body", ""),
        "attachments": [
            {
                "file_name": a.get("file_name", ""),
                "file_url": a.get("file_url", ""),
                "raw_href": a.get("raw_href", ""),
            }
            for a in doc.get("attachments", [])
        ],
    }

    normalized = json.dumps(compare_data, ensure_ascii=False, sort_keys=True)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def make_change_summary(old_doc, new_doc):
    changes = []

    fields_to_check = [
        ("title", "제목"),
        ("notice_type", "고시공고구분"),
        ("notice_no", "고시공고번호"),
        ("date", "작성일"),
        ("department", "담당부서"),
        ("phone", "담당자 연락처"),
        ("body", "본문"),
    ]

    for key, label in fields_to_check:
        old_value = clean_text(old_doc.get(key, ""))
        new_value = clean_text(new_doc.get(key, ""))

        if old_value != new_value:
            changes.append({
                "type": "modified",
                "field": label,
                "old": old_value,
                "new": new_value,
            })

    old_files = {
        a.get("file_name", ""): a
        for a in old_doc.get("attachments", [])
        if a.get("file_name")
    }

    new_files = {
        a.get("file_name", ""): a
        for a in new_doc.get("attachments", [])
        if a.get("file_name")
    }

    for filename in new_files:
        if filename not in old_files:
            changes.append({
                "type": "added",
                "field": "첨부파일",
                "new": filename,
            })

    for filename in old_files:
        if filename not in new_files:
            changes.append({
                "type": "removed",
                "field": "첨부파일",
                "old": filename,
            })

    if not changes:
        return [{
            "type": "system",
            "message": "해시값은 변경되었지만 운영자가 확인할 주요 필드 차이는 찾지 못했습니다."
        }]

    return changes


def attach_change_metadata(doc, old_doc, new_hash):
    detected_at = time.strftime("%Y-%m-%d %H:%M:%S")

    if old_doc:
        doc["change_type"] = "UPDATED_DOCUMENT"
        doc["change_reason"] = "기존 입찰정보 문서 내용이 변경됨"
        doc["change_summary"] = make_change_summary(old_doc, doc)
    else:
        doc["change_type"] = "NEW_DOCUMENT"
        doc["change_reason"] = "신규 입찰정보 문서"
        doc["change_summary"] = [{
            "type": "new",
            "field": "document",
            "message": "새로운 입찰정보 문서가 추가되었습니다."
        }]

    doc["detected_at"] = detected_at
    doc["content_hash"] = new_hash

    return doc


def append_change_history(doc):
    os.makedirs(os.path.dirname(OUTPUT_CHANGE_HISTORY_FILE), exist_ok=True)

    history_item = {
        "detected_at": doc.get("detected_at", ""),
        "change_type": doc.get("change_type", ""),
        "change_reason": doc.get("change_reason", ""),
        "title": doc.get("title", ""),
        "url": doc.get("url", ""),
        "doc_id": doc.get("doc_id", ""),
        "page_type": doc.get("page_type", ""),
        "category": doc.get("category", ""),
        "notice_id": doc.get("notice_id", ""),
        "notice_no": doc.get("notice_no", ""),
        "department": doc.get("department", ""),
        "change_summary": doc.get("change_summary", []),
    }

    with open(OUTPUT_CHANGE_HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(history_item, ensure_ascii=False) + "\n")

# 삭제된 입찰정보 기록용 
def append_deleted_bid_history(doc, reason):
    if reason == "OLD_YEAR":
        change_reason = "현재 연도가 아닌 입찰정보이므로 저장 대상에서 제외"
        message = (
            "현재 연도 공고가 아니므로 입찰정보 데이터에서 제거되었습니다."
        )
    else:
        change_reason = "현재 입찰정보 목록에서 공고가 사라짐"
        message = (
            "입찰정보 목록에서 공고가 사라졌습니다. "
            "공고 기간 종료 또는 사이트 삭제 처리 가능성이 있습니다."
        )

    history_item = {
        "detected_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "change_type": "DELETED_DOCUMENT",
        "change_reason": change_reason,
        "title": doc.get("title", ""),
        "url": doc.get("url", ""),
        "doc_id": doc.get("doc_id", ""),
        "page_type": doc.get("page_type", ""),
        "category": doc.get("category", ""),
        "notice_id": doc.get("notice_id", ""),
        "notice_no": doc.get("notice_no", ""),
        "department": doc.get("department", ""),
        "change_summary": [
            {
                "type": "removed",
                "field": "document",
                "message": message,
            }
        ],
    }

    os.makedirs(
        os.path.dirname(OUTPUT_CHANGE_HISTORY_FILE),
        exist_ok=True,
    )

    with open(
        OUTPUT_CHANGE_HISTORY_FILE,
        "a",
        encoding="utf-8",
    ) as f:
        f.write(json.dumps(history_item, ensure_ascii=False) + "\n")

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
    ensure_dir(DELTA_DIR)
    ensure_dir(HISTORY_DIR)

    crawl_state = load_json_file(STATE_FILE)
    existing_docs = load_existing_docs(OUTPUT_FILE)

    session = requests.Session()

    changed = 0
    unchanged = 0
    deleted = 0

    # 현재 사이트에 실제로 남아 있는 공고 판별용
    current_notice_ids = set()

    # 중복 방문 방지용
    visited_notice_ids = set()

    # 목록 요청이 한 번이라도 정상적으로 성공했는지 확인
    list_crawl_succeeded = False

    start_html = fetch(session, START_URL)

    list_url = extract_bid_list_url(
        start_html,
        START_URL,
    )

    print("입찰정보 목록 URL:", list_url)

    with open(OUTPUT_DELTA_FILE, "w", encoding="utf-8") as delta_out:
        for page in range(1, MAX_LIST_PAGES + 1):
            print(f"[LIST] page={page}")

            try:
                list_html = fetch_list_page(session, page)
                list_crawl_succeeded = True

            except Exception as e:
                print(f"  목록 요청 실패: {e}")
                continue

            detail_links = extract_detail_links(list_html)

            print(f"  상세 링크 수: {len(detail_links)}")
            print("searchDetail 개수:", list_html.count("searchDetail"))
            print("총 글 개수 문구 포함 여부:", "총 <strong>0</strong>개의 글" in list_html)

            if not detail_links:
                print("  상세 링크 없음")
                continue

            for link in detail_links:
                notice_id = link["notice_id"]

                # 현재 입찰정보 목록에 존재하는 공고로 기록
                current_notice_ids.add(notice_id)

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
                    if not is_current_year_bid(doc.get("date", "")):
                        print(
                            f"    저장 안 함: 현재 연도 공고 아님 "
                            f"({doc.get('date', '작성일 없음')})"
                        )
                        continue

                except Exception as e:
                    print(f"    상세 요청 실패: {e}")
                    continue

                if len(doc.get("text", "")) < 80:
                    print("    저장 안 함: 본문 부족")
                    continue

                new_hash = make_content_hash(doc)
                old_hash = crawl_state.get(doc["url"], {}).get("content_hash")

                if old_hash == new_hash:
                    unchanged += 1
                    print(f"    변경 없음: {doc['title']}")
                    continue

                old_doc = existing_docs.get(doc["doc_id"])
                doc = attach_change_metadata(doc, old_doc, new_hash)

                crawl_state[doc["url"]] = {
                    "content_hash": new_hash,
                    "last_crawled": time.strftime("%Y-%m-%d"),
                }

                existing_docs[doc["doc_id"]] = doc

                delta_out.write(json.dumps(doc, ensure_ascii=False) + "\n")
                delta_out.flush()

                append_change_history(doc)

                changed += 1

                if old_doc:
                    print(f"    수정 감지: {doc['title']}")
                else:
                    print(f"    신규 저장: {doc['title']}")

                time.sleep(REQUEST_DELAY)

            time.sleep(REQUEST_DELAY)


    # 현재 입찰정보 목록에서 사라진 기존 공고 삭제 
    # 1. 2026년 이전 연도 공고 2. 현재 연도지만 현재 사이트 목록에서 사라진 공고
    if list_crawl_succeeded:
        removed_doc_ids = []

        removed_docs = {}

        for doc_id, old_doc in existing_docs.items():
            old_notice_id = str(
                old_doc.get("notice_id", "")
            ).strip()

            old_date = old_doc.get("date", "")

            if not is_current_year_bid(old_date):
                removed_docs[doc_id] = "OLD_YEAR"
                continue

            if old_notice_id and old_notice_id not in current_notice_ids:
                removed_docs[doc_id] = "NOT_IN_LIST"
        # 삭제실행
        for doc_id, delete_reason in removed_docs.items():
            removed_doc = existing_docs.pop(doc_id)

            removed_url = removed_doc.get("url", "")

            if removed_url:
                crawl_state.pop(removed_url, None)

            append_deleted_bid_history(
                removed_doc,
                delete_reason,
            )

            deleted += 1

            print(
                f"    입찰공고 삭제: "
                f"{removed_doc.get('title', '')} "
                f"[{delete_reason}]"
            )
    else:
        print(
            "목록 수집에 성공하지 못해 "
            "기존 입찰공고 삭제를 수행하지 않습니다."
        )
    save_existing_docs(OUTPUT_FILE, existing_docs)
    save_json_file(STATE_FILE, crawl_state)

    print("\n입찰정보 크롤링 완료")
    print(f"- 현재 유효 입찰공고 수: {len(existing_docs)}")
    print(f"- 신규/수정 문서 수: {changed}")
    print(f"- 변경 없음: {unchanged}")
    print(f"- 목록에서 삭제된 종료 공고 수: {deleted}")
    print(f"- 전체 파일: {OUTPUT_FILE}")
    print(f"- 변경분 파일: {OUTPUT_DELTA_FILE}")
    print(f"- 변경 이력 파일: {OUTPUT_CHANGE_HISTORY_FILE}")
    
if __name__ == "__main__":
    crawl_bid_pages()