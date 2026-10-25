import asyncio
from app.secure.privacy_guard import privacy_guard

# 모두 가상의 테스트 데이터
TEST_CASES = [
    ("사하구청 위치 알려줘", False),
    ("하단동 대형폐기물 배출 방법 알려줘", False),
    ("사하구청 대표전화번호 알려줘", False),
    ("주민등록등본 발급 방법 알려줘", False),
    ("민원실 운영시간 알려줘", False),
    ("괴정동 주민센터 어디야?", False),

    ("제 이름은 김민수입니다", True),
    ("나 박지민인데 전입신고 어떻게 해?", True),
    ("김철수인데 사하구청 주소 알려줘", True),

    ("제 전화번호는 010-1234-5678입니다", True),
    ("01012345678로 연락해 주세요", True),
    ("이메일은 test@example.com입니다", True),

    ("부산광역시 사하구 하단동 123-45에 살아요", True),
    ("부산광역시 사하구 낙동대로 100에 살아요", True),

    ("주민등록번호는 900101-1234567입니다", True),
    ("계좌번호는 123-456-789012입니다", True),

    ("김민수이고 번호는 010-1234-5678입니다", True),
    ("사하구청 전화번호와 주소 알려줘", False),
]

async def main():
    tp = tn = fp = fn = blocked = 0

    for i, (question, has_pii) in enumerate(TEST_CASES, 1):
        try:
            result = await privacy_guard(question)
            detected = result != question

            if has_pii and detected:
                status = "PASS"
                tp += 1
            elif not has_pii and not detected:
                status = "PASS"
                tn += 1
            elif not has_pii and detected:
                status = "FALSE POSITIVE"
                fp += 1
            else:
                status = "MISSED"
                fn += 1

        except Exception as e:
            status = f"BLOCKED ({type(e).__name__})"
            blocked += 1

        # 개인정보 원문은 출력하지 않음
        print(f"{i:02d}. {status}")

    print("\n===== 테스트 결과 =====")
    print(f"정상 개인정보 처리: {tp}")
    print(f"정상 일반 질문: {tn}")
    print(f"오탐: {fp}")
    print(f"탐지 누락 의심: {fn}")
    print(f"차단: {blocked}")
    print(f"전체 테스트: {len(TEST_CASES)}")

asyncio.run(main())
