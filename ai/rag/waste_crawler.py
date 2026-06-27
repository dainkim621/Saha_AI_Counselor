import os
import re
import json
import time
import hashlib
from urllib.parse import urlparse, parse_qs

import requests
from bs4 import BeautifulSoup, NavigableString

### 폐기물 ###
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
    # 본문 내용은 없고 링크 이동
    {
        "url": "https://www.saha.go.kr/portal/contents.do?mId=0405050600",
        "category": "의료폐기물 분류·관리방법 안내",
        "topic": "의료폐기물 분류·관리방법 안내",
        
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

# 필요없는 문구
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
        "공유",
        "인쇄하기",
        "프린트",
    }

    lines = []

    for line in text.splitlines():
        line = clean_inline(line)

        if not line:
            continue

        if line in noise_exact:
            continue

        lines.append(line)

    return "\n".join(lines).strip()

def select_main_content(soup):
    # 사하구청 본문 영역 우선 선택
    for selector in ["#conts", "#contents", "#content", ".contents", ".content"]:
        node = soup.select_one(selector)
        if node:
            text = clean_text(node.get_text("\n", strip=True))
            if len(text) >= 50:
                return node

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

    text = "\n".join(lines)
    text = remove_noise_lines(text)

    return text

def looks_like_heading(text):
    text = clean_inline(text)

    if not text:
        return False

    # 너무 짧거나 너무 긴 경우
    if len(text) < 2:
        return False

    if len(text) > 50:
        return False

    # URL
    if re.search(r"https?://|www\.", text):
        return False

    # 전화번호
    if re.search(r"\d{2,4}-\d{3,4}-\d{4}", text):
        return False

    # 주의문
    if text.startswith(("※", "-", "·", "ㆍ")):
        return False

    # 문장형 종결어미
    if text.endswith((
        "입니다",
        "합니다",
        "됩니다",
        "있습니다",
        "없습니다",
        "바랍니다",
        "하십시오",
        "하세요",
        "가능합니다",
    )):
        return False

    # 명시적으로 제목으로 인정
    if text in [
        "배출일시",
        "배출방법",
        "다량배출사업장이란?",
        "대형폐가전 : 무상수거",
        "소형폐가전 : 무상수거",
    ]:
        return True

    # 콜론 포함 처리
    if ":" in text or "：" in text:

        left, right = re.split(r"[:：]", text, 1)

        left = clean_inline(left)
        right = clean_inline(right)

        # "대 상 : 아래 품목" 같은 설명형
        if len(left) <= 3:
            return False

        # 값 설명형
        if any(
            keyword in right
            for keyword in [
                "아래",
                "매주",
                "상시",
                "인터넷",
                "콜센터",
                "요일",
                "배출",
                "품목",
                "수거함",
                "전화",
                "문의",
                "신청",
                "방법",
            ]
        ):
            return False

        # 숫자 위주
        if re.search(r"\d", right):
            return False

        # 제목형
        if len(text) <= 30:
            return True

        # 대형폐기물 표 제목이 긴 괄호 포함 제목
        if "수수료" in text and ("대형폐기물" in text or "폐기물" in text):
            return True

        return False

    # 일반 제목 패턴
    if text.endswith((
        "안내",
        "방법",
        "절차",
        "대상",
        "기준",
        "발급",
        "신고",
        "처리",
        "수거",
    )):
        return True

    # 물음표 제목
    if text.endswith("?"):
        return True

    # 일반적인 짧은 제목
    words = text.split()

    if len(words) <= 5 and len(text) <= 30:
        return True

    return False

#소제목
def is_list_heading(text):
    text = clean_inline(text)

    if not text:
        return False

    # 너무 긴 문장은 제외
    if len(text) > 50:
        return False

    # URL 제외
    if re.search(r"https?://|www\.", text):
        return False

    # 전화번호 제외
    if re.search(r"\d{2,4}-\d{3,4}-\d{4}", text):
        return False

    # 목록 문장 제외
    if text.startswith(("※", "-", "·", "ㆍ")):
        return False

    # 내용형 문장 제외
    if any(
        word in text
        for word in [
            "경우",
            "배출",
            "신청",
            "처리",
            "사용",
            "문의",
            "수거",
            "가능",
            "불가",
        ]
    ):
        if len(text) > 25:
            return False

    # 제목 패턴
    if text.endswith((
        "안내",
        "사항",
        "대상",
        "방법",
        "절차",
        "기준",
        "요령",
        "업체",
    )):
        return True

    # 매우 짧은 독립 문장
    if len(text) <= 20:
        return True

    return False

def normalize_heading(text):
    text = clean_inline(text)
    text = text.replace("페가전", "폐가전")
    text = re.sub(r"\s+", "", text)
    return text


def is_bad_heading(text, page_title):
    text = clean_inline(text)

    if not text:
        return True

    # 메뉴/브레드크럼 성격의 단어 제외
    if text in [
        "Home",
        "분야별정보",
        "환경/청소",
        "폐기물",
    ]:
        return True

    # 페이지 제목과 같은 heading은 중복 제외
    if normalize_heading(text) == normalize_heading(page_title):
        return True

    # 표 컬럼명 제외
    if text in ["분류", "분 류", "품명", "품 명"]:
        return True

    return False

def normalize_heading(text):
    text = clean_inline(text)
    text = text.replace("페가전", "폐가전")
    text = re.sub(r"\s+", "", text)
    return text


def is_bad_heading(text, page_title):
    text = clean_inline(text)

    if not text:
        return True

    # 메뉴/브레드크럼 성격의 단어 제외
    if text in [
        "Home",
        "분야별정보",
        "환경/청소",
        "폐기물",
    ]:
        return True

    # 페이지 제목과 같은 heading은 중복 제외
    if normalize_heading(text) == normalize_heading(page_title):
        return True

    # 표 컬럼명 제외
    if text in ["분류", "분 류", "품명", "품 명"]:
        return True

    return False

def is_weekday_table(table):
    caption = clean_inline(table.find("caption").get_text(" ", strip=True)) if table.find("caption") else ""
    text = clean_inline(table.get_text(" ", strip=True))

    return (
        "쓰레기 배출요일" in caption
        or (
            "배출요일" in text
            and "쓰레기" in text
            and all(day in text for day in ["월", "화", "수", "목", "금", "토", "일"])
        )
    )


def extract_weekday_table_sections(table, base_path):
    sections = []

    # thead에서 요일 추출
    header_cells = table.select("thead tr th")
    headers = [
        clean_inline(th.get_text(" ", strip=True))
        for th in header_cells
    ]

    # ["배출요일", "월", "화", ...] 에서 요일만 사용
    days = headers[1:]

    # tbody 첫 번째 행의 td들 추출
    body_row = table.select_one("tbody tr")

    if not body_row:
        return sections

    body_cells = body_row.find_all("td", recursive=False)

    # 첫 번째 td는 "쓰레기 종류" 라벨
    values = body_cells[1:]

    for day, td in zip(days, values):
        day = clean_inline(day)

        item_text = clean_block_text(
            td.get_text("\n", strip=True)
        )

        item_text = remove_noise_lines(item_text)

        if not day or not item_text:
            continue

        sections.append({
            "heading_path": base_path + [day],
            "block_type": "table_row",
            "text": text,
        })

    return sections

def extract_weekday_table_sections(table, base_path):
    sections = []

    headers = [
        clean_inline(th.get_text(" ", strip=True))
        for th in table.select("thead tr th")
    ]

    days = headers[1:]

    body_row = table.select_one("tbody tr")
    if not body_row:
        return sections

    body_cells = body_row.find_all("td", recursive=False)
    values = body_cells[1:]

    for day, td in zip(days, values):
        item_text = clean_block_text(td.get_text("\n", strip=True))
        item_text = remove_noise_lines(item_text)

        if not day or not item_text:
            continue

        sections.append({
            "heading_path": base_path + ["쓰레기 배출요일", day],
            "block_type": "table_row",
            "text": item_text,
        })

    return sections


def extract_company_table_sections(table, base_path):
    sections = []

    for tr in table.select("tbody tr"):
        cells = [
            clean_inline(td.get_text(" ", strip=True))
            for td in tr.find_all("td", recursive=False)
        ]

        if len(cells) < 3:
            continue

        company, area, phone = cells[0], cells[1], cells[2]

        sections.append({
            "heading_path": base_path + [company],
            "block_type": "table_row",
            "text": f"담당구역: {area}\n전화번호: {phone}",
        })

    return sections
# 매트릭스 표 처리
def extract_price_matrix_table_sections(table, base_path):

    sections = []

    rows = []

    for tr in table.find_all("tr"):
        cells = [
            clean_inline(cell.get_text(" ", strip=True))
            for cell in tr.find_all(["th", "td"], recursive=False)
        ]

        cells = [c for c in cells if c]

        if cells:
            rows.append(cells)

    if len(rows) < 2:
        return sections

    header = rows[0]
    categories = header[1:]

    # 행을 dict로 변환
    row_map = {}

    for row in rows[1:]:
        if len(row) < 2:
            continue

        label = row[0]
        values = row[1:]

        row_map[label] = values

    # 용기규격 행이 있으면 열 제목에 같이 사용
    specs = row_map.get("용기규격", [])

    max_cols = max(
        len(categories),
        len(specs),
        *[len(v) for v in row_map.values()]
    )

    for idx in range(max_cols):
        category = categories[idx] if idx < len(categories) else ""
        spec = specs[idx] if idx < len(specs) else ""

        if not category:
            continue

        # heading_path: 일반가정용 > 3ℓ
        heading = base_path + [category]

        if spec:
            heading.append(spec)

        lines = []

        for label, values in row_map.items():
            if label == "용기규격":
                continue

            value = values[idx] if idx < len(values) else ""

            if not value:
                continue

            lines.append(f"{label}: {value}")

        if not lines:
            continue

        sections.append({
            "heading_path": heading,
            "block_type": "table_column",
            "text": "\n".join(lines),
        })

    return sections

# 대형폐기물 수집 및 운반 처리 수수료 표 전용 처리.
def extract_large_waste_fee_table_sections(table, base_path):
    
    sections = []
    rows = []
    rowspan_map = {}

    tbody = table.find("tbody")
    if not tbody:
        return sections

    trs = tbody.find_all("tr", recursive=False)

    for r_idx, tr in enumerate(trs):
        row = []
        c_idx = 0

        cells = tr.find_all(["th", "td"], recursive=False)

        for cell in cells:
            while (r_idx, c_idx) in rowspan_map:
                row.append(rowspan_map[(r_idx, c_idx)])
                c_idx += 1

            text = clean_inline(cell.get_text(" ", strip=True))

            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))

            for _ in range(colspan):
                row.append(text)

                if rowspan > 1:
                    for rr in range(1, rowspan):
                        rowspan_map[(r_idx + rr, c_idx)] = text

                c_idx += 1

        while (r_idx, c_idx) in rowspan_map:
            row.append(rowspan_map[(r_idx, c_idx)])
            c_idx += 1

        if row:
            rows.append(row)

    for row in rows:
        # 기대 구조:
        # 0 유형, 1 품명번호, 2 품명, 3 규격번호, 4 규격, 5 계, 6 수집·운반비, 7 처리비
        if len(row) < 8:
            continue

        waste_type = clean_inline(row[0])
        item_name = clean_inline(row[2])
        spec = clean_inline(row[4])
        total_fee = clean_inline(row[5])
        collect_fee = clean_inline(row[6])
        process_fee = clean_inline(row[7])

        if not waste_type or not item_name or not spec or not total_fee:
            continue

        sections.append({
            # 소제목 잘라내지 않게 수정
            "heading_path": base_path + [
                waste_type,
                item_name,
            ],
            "block_type": "table_row",
            "text": (
                f"품명: {item_name}\n"
                f"규격: {spec}\n"
                f"수수료 계: {total_fee}\n"
                f"수집·운반비: {collect_fee}\n"
                f"처리비: {process_fee}"
            ),
        })

    return sections

# 폐가전 표처럼 대분류 / 세부분류 / 품목 구조인 표 처리.
def extract_general_table_sections(table, base_path):
  
    sections = []
    rows = []
    rowspan_map = {}

    trs = table.find_all("tr")

    for r_idx, tr in enumerate(trs):
        row = []
        c_idx = 0

        cells = tr.find_all(["th", "td"])

        for cell in cells:
            while (r_idx, c_idx) in rowspan_map:
                row.append(rowspan_map[(r_idx, c_idx)])
                c_idx += 1

            text = clean_inline(cell.get_text(" ", strip=True))
            text = text.replace(" ", "")

            rowspan = int(cell.get("rowspan", 1))
            colspan = int(cell.get("colspan", 1))

            for _ in range(colspan):
                row.append(text)

                if rowspan > 1:
                    for rr in range(1, rowspan):
                        rowspan_map[(r_idx + rr, c_idx)] = text

                c_idx += 1

        while (r_idx, c_idx) in rowspan_map:
            row.append(rowspan_map[(r_idx, c_idx)])
            c_idx += 1

        row = [x for x in row if x]

        if row:
            rows.append(row)

    for row in rows:
        row = [
            x for x in row
            if x not in ["분류", "분 류", "품명", "품 명"]
        ]

        if not row:
            continue

        if len(row) >= 3:
            big = row[0]
            sub = row[1]
            item = " ".join(row[2:]).strip()

            if big and sub and item:
                sections.append({
                    "heading_path": base_path + [big, sub],
                    "block_type": "table_row",
                    "text": item,
                })

        elif len(row) == 2:
            sections.append({
                "heading_path": base_path + [row[0]],
                "block_type": "table_row",
                "text": row[1],
            })

    return sections

# 품목 / 배출요령 형태의 표 처리.
def extract_item_guide_table_sections(table, base_path):
    sections = []

    page_title = base_path[0] if base_path else "음식물쓰레기 배출요령"

    for tr in table.select("tbody tr"):
        cells = [
            clean_block_text(td.get_text("\n", strip=True))
            for td in tr.find_all("td", recursive=False)
        ]

        if len(cells) < 3:
            continue

        item = clean_inline(cells[0])
        guide = clean_block_text(cells[1])
        not_allowed = clean_block_text(cells[2])

        if item and guide:
            sections.append({
                "heading_path": [page_title, "배출요령", item],
                "block_type": "table_row",
                "text": guide,
            })

        if not_allowed:
            sections.append({
                "heading_path": [page_title, "음식물 전용용기에 넣어서는 안되는 물질"],
                "block_type": "table_row",
                "text": not_allowed,
            })

    return sections

# 표 -> 텍스트
def table_to_sections(table, base_path):
    sections = []
    # caption은 표 종류 판별용
    caption = ""
    if table.find("caption"):
        caption = clean_inline(
            table.find("caption").get_text(" ", strip=True)
        )

    table_text = clean_inline(table.get_text(" ", strip=True))

    # 1. 대형폐기물 수수료표
    if "대형폐기물 수집 및 운반 처리 수수료" in caption:
        return extract_large_waste_fee_table_sections(table, base_path)

    # 2. 음식물쓰레기 배출요령표
    if "음식물쓰레기" in caption and "배출요령" in caption:
        return extract_item_guide_table_sections(table, base_path)

    # 3. 쓰레기 배출요일표
    if "쓰레기 배출요일" in caption:
        return extract_weekday_table_sections(table, base_path)

    # 4. 생활폐기물 수집·운반업체 표
    if "수집 및 운반업체" in caption:
        return extract_company_table_sections(table, base_path)

    # 5. 쓰레기 규격봉투 가격표
    if "규격봉투 가격표" in caption:
        return extract_price_matrix_table_sections(table, base_path)

    # 6. 음식물쓰레기 전용용기 가격표 및 수수료
    if "음식물쓰레기 전용용기" in caption:
        return extract_price_matrix_table_sections(table, base_path)

    # 7. 품목 / 배출요령 구조인데 caption이 애매한 경우 보조 처리
    if "품목" in table_text and "배출요령" in table_text:
        item_sections = extract_item_guide_table_sections(table, base_path)
        if item_sections:
            return item_sections

    # 8. 그 외 일반 표
    return extract_general_table_sections(table, base_path)

# 현재 태그의 직접 텍스트만 추출한다.
def get_direct_text(node):
    if not node:
        return ""

    texts = []

    for child in node.children:
        if isinstance(child, NavigableString):
            txt = clean_inline(str(child))
            if txt:
                texts.append(txt)

    return " ".join(texts).strip()

def is_bad_table_title(text):
    text = clean_inline(text)

    if not text:
        return True

    # 다운로드/첨부 링크는 제목 아님
    if "다운로드" in text:
        return True

    if text.endswith((".hwp", ".pdf", ".xlsx", ".xls")):
        return True

    # 너무 짧은 일반 단어 제외
    if text in ["다운로드", "보기", "첨부파일"]:
        return True

    return False

# 표의 실제 본문 소제목을 찾는다. caption 사용x
def find_table_title(table, page_title):
    parent_li = table.find_parent("li")

    if parent_li:
        direct_title = get_direct_text(parent_li)

        if direct_title and not is_bad_table_title(direct_title):
            return direct_title

    return ""

# li 바로 아래에 있는 하위 ul/ol의 li 목록만 추출한다.
def child_list_to_text(li):
    child_list = li.find(["ul", "ol"], recursive=False)

    if not child_list:
        return ""

    items = []

    for child_li in child_list.find_all("li", recursive=False):
        txt = clean_block_text(
            child_li.get_text("\n", strip=True)
        )
        txt = remove_noise_lines(txt)

        if txt:
            items.append(txt)

    return "\n".join(items)

def list_to_text(node):
    # table을 포함한 큰 ul/li는 표 원문까지 먹으므로 제외
    if node.find("table"):
        return ""

    items = []

    for li in node.find_all("li", recursive=False):
        if li.find("table"):
            continue

        txt = clean_block_text(li.get_text("\n", strip=True))

        if txt:
            items.append(txt)

    return "\n".join(items)

def extract_structured_sections(main_node, page_title):
    sections = []
    seen = set()

    heading_stack = [{
        "level": 1,
        "title": page_title
    }]

    def current_path():
        return [h["title"] for h in heading_stack]

    def push_heading(level, title):
        nonlocal heading_stack

        title = clean_inline(title)

        if is_bad_heading(title, page_title):
            return

        while heading_stack and heading_stack[-1]["level"] >= level:
            heading_stack.pop()

        heading_stack.append({
            "level": level,
            "title": title
        })

    def add_section(block_type, text):
        text = clean_block_text(text)
        text = remove_noise_lines(text)
        text = clean_text(text)

        if not text:
            return

        heading_path = current_path()

        key = (
            tuple(heading_path),
            block_type,
            text
        )

        if key in seen:
            return

        seen.add(key)

        sections.append({
            "heading_path": heading_path,
            "block_type": block_type,
            "text": text,
        })

    for node in main_node.find_all(
        ["h1", "h2", "h3", "h4", "h5", "h6",
         "strong", "dt",
         "p", "div",
         "ul", "ol",
         "table", "dl"],
        recursive=True
    ):
        # Heading
        if node.name and re.fullmatch(r"h[1-6]", node.name):
            title = clean_inline(
                node.get_text(" ", strip=True)
            )

            if looks_like_heading(title):
                push_heading(
                    int(node.name[1]),
                    title
                )

            continue

        if node.name in ["strong", "dt"]:

            title = clean_inline(
                node.get_text(" ", strip=True)
            )

            if looks_like_heading(title):
                push_heading(5, title)

            continue

        # 표 처리
        if node.name == "table":
            parent_li = node.find_parent("li")

            direct_title = ""
            if parent_li:
                direct_title = get_direct_text(parent_li)

            if direct_title:
                table_base_path = [page_title, direct_title]
            else:
                table_base_path = current_path()

            table_sections = table_to_sections(node, table_base_path)

            for sec in table_sections:
                key = (
                    tuple(sec["heading_path"]),
                    sec["block_type"],
                    sec["text"],
                )

                if key in seen:
                    continue

                seen.add(key)
                sections.append(sec)

            continue

        # List
        if node.name in ["ul", "ol"]:

            # 중첩 ul/ol은 부모 li에서 처리하므로 건너뜀
            if node.find_parent(["ul", "ol"]):
                continue

            pending_items = []

            def flush_pending():
                nonlocal pending_items

                if pending_items:
                    add_section("list", "\n".join(pending_items))
                    pending_items = []

            for li in node.find_all("li", recursive=False):
                direct_title = get_direct_text(li)

                has_child_list = li.find(["ul", "ol"], recursive=False) is not None
                has_table = li.find("table") is not None

                # 자식 ul/table이 있고, 직접 텍스트가 제목처럼 보일 때만 heading 처리
                if direct_title and (has_child_list or has_table) and looks_like_heading(direct_title):
                    flush_pending()
                    push_heading(5, direct_title)

                    child_text = child_list_to_text(li)

                    if child_text:
                        add_section("list", child_text)
                    continue

                # 제목이 아닌 일반 li
                if has_table:
                    continue

                li_text = clean_block_text(
                    li.get_text("\n", strip=True)
                )
                li_text = remove_noise_lines(li_text)

                if li_text:
                    pending_items.append(li_text)

            flush_pending()

            continue

        # Paragraph / Div
        if node.name in ["p", "div"]:

            # 표를 포함하는 div는 스킵
            if node.find("table"):
                continue

            text = clean_block_text(
                node.get_text("\n", strip=True)
            )

            lines = [
                clean_inline(x)
                for x in text.splitlines()
                if clean_inline(x)
            ]

            if (
                len(lines) == 1
                and looks_like_heading(lines[0])
            ):
                push_heading(5, lines[0])
                continue

            add_section("paragraph", text)

            continue

        # Definition List
        if node.name == "dl":

            add_section(
                "definition_list",
                node.get_text("\n", strip=True)
            )

            continue

    return sections

def extract_key_sections(text):
    # RAG 검색 정확도를 위해 배출방법/수수료/신고기준 관련 문장을 별도 필드로 뽑는다.
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

    # body_text = clean_text(main_node.get_text("\n", strip=True)) if main_node else ""
    sections = extract_structured_sections(main_node, page_info["topic"]) if main_node else []
    if sections is None:
        sections = []

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
    "[섹션 구조]",
    ]

    for sec in sections:
        block_type = sec.get("block_type", "")

        # 전체 본문 백업은 최종 text에 넣지 않음
        if block_type == "full_text_backup":
            continue

        path = " > ".join(sec.get("heading_path", []))
        sec_text = sec.get("text", "")

        if path:
            parts.append(f"[SECTION] {path}")

        if block_type == "table_row":
            parts.append(sec_text)
        elif block_type == "table":
            parts.append("[표]\n" + sec_text)
        elif block_type == "list":
            parts.append("[목록]\n" + sec_text)
        else:
            parts.append(sec_text)


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
        "sections": sections,
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