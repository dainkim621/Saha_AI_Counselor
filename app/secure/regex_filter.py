#app/secure/regex_filter.py
import re


class PrivacyBlocked(Exception):
    """개인정보 보호 정책에 따라 질문을 차단할 때 사용"""
    pass


PATTERNS = {
    # 주민등록번호 형태
    "RRN": re.compile(
        r"(?<!\d)\d{6}\s*[-]?\s*[1-8]\d{6}(?!\d)"
    ),

    # 휴대전화번호
    "PHONE": re.compile(
        r"(?<!\d)01[016789][-\s]?\d{3,4}[-\s]?\d{4}(?!\d)"
    ),

    # 이메일
    "EMAIL": re.compile(
        r"(?<![\w.+-])[\w.+-]+@"
        r"(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,}"
    ),
}


def regex_filter(text: str, max_length: int = 3000) -> str:
    if not isinstance(text, str):
        raise PrivacyBlocked("잘못된 입력 형식")

    if not text.strip() or len(text) > max_length:
        raise PrivacyBlocked("잘못된 입력 길이")

    # 주민등록번호 발견 시 전체 질문 차단
    if PATTERNS["RRN"].search(text):
        raise PrivacyBlocked("민감한 식별번호 탐지")

    # 전화번호 마스킹
    text = PATTERNS["PHONE"].sub(
        "[전화번호]", text
    )

    # 이메일 마스킹
    text = PATTERNS["EMAIL"].sub(
        "[이메일]", text
    )

    return text
