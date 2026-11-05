#app/secure/privacy_guard.py
from app.secure.regex_filter import regex_filter, PrivacyBlocked
from app.secure.gemma_detector import detect_personal_info
import logging

MASK_LABELS = {
    "PERSON": "[이름]",
    "ADDRESS": "[상세주소]",
    "PHONE": "[전화번호]",
    "EMAIL": "[이메일]",
    "ACCOUNT": "[계좌번호]",
    "ID_NUMBER": "[식별번호]"
}

BLOCK_TYPES = {"ACCOUNT", "ID_NUMBER"}

async def privacy_guard(question, max_length=3000):
    cleaned = regex_filter(question, max_length=max_length)

    

    logger = logging.getLogger(__name__)

    try:
        entities = await detect_personal_info(cleaned)

    except Exception as e:
        logger.error(
            "Gemma 개인정보 검사 실패: %s",
            type(e).__name__
        )
        raise PrivacyBlocked("Gemma 개인정보 탐지 실패") from e

    if any(e["type"] in BLOCK_TYPES for e in entities):
        raise PrivacyBlocked("민감한 개인정보 탐지")
    # 공공기관 명칭이 상세주소로 잘못 탐지되는 경우 방지
    PUBLIC_OFFICES = {"사하구청"}

    entities = [
        entity for entity in entities
        if not (
            entity["type"] == "ADDRESS"
            and entity["text"] in PUBLIC_OFFICES
        )
    ]

    entities.sort(key=lambda e: len(e["text"]), reverse=True)

    for entity in entities:
        cleaned = cleaned.replace(
            entity["text"],
            MASK_LABELS[entity["type"]]
        )

    cleaned = regex_filter(cleaned, max_length=max_length)

    return cleaned

