#app/secure/privacy_guard.py
from app.secure.regex_filter import regex_filter, PrivacyBlocked
from app.secure.gemma_detector import detect_personal_info

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

    try:
        entities = await detect_personal_info(cleaned)
    except Exception:
        raise PrivacyBlocked("Gemma 개인정보 탐지 실패")

    if any(e["type"] in BLOCK_TYPES for e in entities):
        raise PrivacyBlocked("민감한 개인정보 탐지")

    entities.sort(key=lambda e: len(e["text"]), reverse=True)

    for entity in entities:
        cleaned = cleaned.replace(
            entity["text"],
            MASK_LABELS[entity["type"]]
        )

    cleaned = regex_filter(cleaned, max_length=max_length)

    return cleaned

