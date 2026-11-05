from app.secure.regex_filter import regex_filter, PrivacyBlocked

questions = [
    "하단동 대형폐기물 배출 방법 알려줘",
    "제 전화번호는 010-1234-5678입니다",
    "이메일은 test@example.com입니다",
    "제 이름은 김민수입니다",
    "제 번호는 공일공 일이삼사 오육칠팔이에요",
    "주민등록번호는 900101-1234567입니다"
]

for index, question in enumerate(questions, 1):
    try:
        result = regex_filter(question)

        print(f"\n[테스트 {index}]")
        print("결과:", result)

    except PrivacyBlocked:
        print(f"\n[테스트 {index}]")
        print("결과: 개인정보 보호 정책에 따라 차단")
