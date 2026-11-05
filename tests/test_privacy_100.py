
import asyncio
import csv
import re
from pathlib import Path

from app.secure.privacy_guard import privacy_guard

BASE = Path(__file__).resolve().parent
INPUT = BASE / "saha_privacy_test_100.csv"
OUTPUT = BASE / "privacy_test_results.csv"

# 개인정보 마스킹에 사용하는 표시
MASK_PATTERN = re.compile(
    r"\[(이름|전화번호|이메일|계좌|주민등록번호)\]"
)

async def evaluate(question):
    try:
        result = await privacy_guard(question)

        # 반환값이 문자열인 경우
        if not isinstance(result, str):
            return "ERROR", False, str(result)

        masked = bool(MASK_PATTERN.search(result))
        return (
            "MASKED" if masked else "PASSED",
            masked,
            result
        )

    except Exception as e:
        if type(e).__name__ == "PrivacyBlocked":
            return "BLOCKED", True, "PrivacyBlocked"

        return "ERROR", False, f"{type(e).__name__}: {e}"


async def main():
    with INPUT.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))

    tp = fp = tn = fn = errors = 0

    for i, row in enumerate(rows, 1):
        question = row["테스트 질문"]
        expected = row["개인정보 포함 예상(Y/N)"].strip().upper() == "Y"

        status, detected, result = await evaluate(question)

        row["실제 탐지(Y/N)"] = (
            "ERROR" if status == "ERROR"
            else "Y" if detected else "N"
        )
        row["실제 처리 결과"] = status
        row["검토 메모"] = (
            "오류: " + result if status == "ERROR"
            else "자동 판정 - 수동 검토 필요"
        )

        if status == "ERROR":
            errors += 1
        elif expected and detected:
            tp += 1
        elif expected and not detected:
            fn += 1
        elif not expected and detected:
            fp += 1
        else:
            tn += 1

        print(f"[{i}/{len(rows)}] {status} | {question[:35]}")

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)

    def pct(a, b):
        return round(100 * a / b, 2) if b else 0

    print("\n===== 개인정보 탐지 테스트 결과 =====")
    print(f"전체 질문: {len(rows)}건")
    print(f"TP={tp}, FN={fn}, FP={fp}, TN={tn}")
    print(f"오류: {errors}건")
    print(f"탐지율: {pct(tp, tp + fn)}%")
    print(f"정밀도: {pct(tp, tp + fp)}%")
    print(f"오탐률: {pct(fp, fp + tn)}%")
    print(f"결과 파일: {OUTPUT}")

asyncio.run(main())
