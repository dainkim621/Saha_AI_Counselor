import os
import re
import json
import hashlib
from pypdf import PdfReader

# 외교부 여권 서식 페이지 : PDF 다운로드 링크를 바로 가져오기 어려움. 
# 외교부 사이트가 PDF 다운로드를 JS/브라우저 동작 기반으로 처리하기 때문.
# 우리가 로컬에 저장한 PDF를 FastAPI가 제공하는 file_url 제공..


PDF_DIR = "data/raw/passport_pdfs"
OUTPUT_JSONL = "data/raw/passport_forms.jsonl"
#외교부 여권서식 페이지만
SOURCE_URL = "https://www.passport.go.kr/home/kor/applicationForm/index.do?menuPos=42"


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]*\n+", "\n\n", text)
    return text.strip()


def make_doc_id(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()


def filename_to_title(filename: str) -> str:
    name = os.path.splitext(filename)[0]
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name)
    return name.strip()

# 로컬 첨부파일 기반
def make_local_file_url(pdf_file: str) -> str:
    return f"/files/passport_pdfs/{pdf_file}"


def extract_pdf_text(pdf_path: str) -> str:
    try:
        reader = PdfReader(pdf_path)
        pages = []

        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        return clean_text("\n\n".join(pages))

    except Exception as e:
        print(f"  PDF 읽기 실패: {pdf_path} / {e}")
        return ""


def crawl_local_passport_pdfs():
    if not os.path.exists(PDF_DIR):
        print(f"PDF 폴더가 없습니다: {PDF_DIR}")
        return

    pdf_files = [
        f for f in os.listdir(PDF_DIR)
        if f.lower().endswith(".pdf")
    ]

    if not pdf_files:
        print(f"PDF 파일이 없습니다: {PDF_DIR}")
        return

    saved_count = 0

    with open(OUTPUT_JSONL, "w", encoding="utf-8") as f:
        for pdf_file in sorted(pdf_files):
            pdf_path = os.path.join(PDF_DIR, pdf_file)

            title = filename_to_title(pdf_file)
            pdf_text = extract_pdf_text(pdf_path)

            if not pdf_text:
                print(f"  저장 안 함: PDF 텍스트 없음 / {pdf_file}")
                continue

            text = clean_text(f"""
                제목: {title}
                메뉴경로: 외교부 여권안내 > 여권기본사항 > 신청서식 모음
                출처페이지: {SOURCE_URL}

                [서식 정보]
                서식명: {title}
                파일명: {pdf_file}

                [PDF 본문]
                {pdf_text}
                """)

            doc = {
                "doc_id": make_doc_id(f"passport.go.kr::{pdf_file}"),
                "url": SOURCE_URL,
                "parent_url": "",
                "anchor_text": title,
                "menu_path": ["외교부 여권안내", "여권기본사항", "신청서식 모음"],
                "page_type": "passport_form_pdf",
                "title": title,
                "author": "외교부 여권과",
                "date": "",
                "views": "",
                "text": text,
                "paragraphs": [p for p in text.split("\n") if p.strip()],
                "source": "passport.go.kr",
                "attachments": [
                    {
                        "filename": pdf_file,
                        "file_url": make_local_file_url(pdf_file),
                        "file_path": pdf_path,
                        "extension": "pdf",
                        "source_type": "local_pdf",
                    }
                ],
                "attachment_count": 1,

            }

            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
            saved_count += 1

            print(f"  저장 완료 ({saved_count}): {title}")

    print("\n외교부 여권 PDF 서식 크롤링 완료")
    print(f"- PDF 폴더: {PDF_DIR}")
    print(f"- 저장 문서 수: {saved_count}")
    print(f"- 출력 파일: {OUTPUT_JSONL}")


if __name__ == "__main__":
    crawl_local_passport_pdfs()
