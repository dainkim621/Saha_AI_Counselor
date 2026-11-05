
import asyncio
from unittest.mock import patch

from app.secure.privacy_guard import privacy_guard
from app.secure.regex_filter import PrivacyBlocked
import unittest
from unittest.mock import AsyncMock

# 실제 Gemma 대신 사용하는 가짜 탐지 함수
async def mock_gemma(text):
    entities = []

    if "김민수" in text:
        entities.append({
            "text": "김민수",
            "type": "PERSON"
        })

    if "공일공 일이삼사 오육칠팔" in text:
        entities.append({
            "text": "공일공 일이삼사 오육칠팔",
            "type": "PHONE"
        })

    if "123-456-789" in text:
        entities.append({
            "text": "123-456-789",
            "type": "ACCOUNT"
        })

    return entities


async def main():
    questions = [
        "하단동 대형폐기물 배출 방법 알려줘",
        "제 전화번호는 010-1234-5678입니다",
        "제 이름은 김민수입니다",
        "제 번호는 공일공 일이삼사 오육칠팔이에요",
        "제 계좌번호는 123-456-789입니다"
    ]

    with patch(
        "app.secure.privacy_guard.detect_personal_info",
        new=mock_gemma
    ):
        for question in questions:
            try:
                result = await privacy_guard(question)
                print("변환 결과:", result)

            except PrivacyBlocked:
                print("개인정보 보호 정책에 따라 차단")



async def test_connection_failure():
    async def broken_gemma(text):
        raise ConnectionError("Gemma 서버 연결 실패")

    with patch(
        "app.secure.privacy_guard.detect_personal_info",
        new=broken_gemma
    ):
        try:
            await privacy_guard("대형폐기물 신청 방법")
            print("실패: 질문이 통과되었습니다")

        except PrivacyBlocked:
            print("성공: Gemma 연결 실패 시 질문 차단")




class TestPrivacyMasking(unittest.IsolatedAsyncioTestCase):

    async def test_name_and_address_masking(self):
        question = "김민수는 부산시 사하구 낙동대로 123에 살아요."

        fake_entities = [
            {
                "text": "김민수",
                "type": "PERSON"
            },
            {
                "text": "부산시 사하구 낙동대로 123",
                "type": "ADDRESS"
            }
        ]

        with patch(
            "app.secure.privacy_guard.detect_personal_info",
            new_callable=AsyncMock,
            return_value=fake_entities
        ):
            result = await privacy_guard(question)

        self.assertNotIn("김민수", result)
        self.assertNotIn("낙동대로 123", result)

        self.assertIn("[이름]", result)
        self.assertIn("[상세주소]", result)
        
    async def test_long_rag_context(self):
        from unittest.mock import AsyncMock

        # 3,000자를 초과하는 가짜 RAG 문서
        long_context = "대형폐기물 배출 안내입니다. " * 300

        self.assertGreater(len(long_context), 3000)

        with patch(
            "app.secure.privacy_guard.detect_personal_info",
            new_callable=AsyncMock,
            return_value=[]
        ) as gemma_mock:

            result = await privacy_guard(
                long_context,
                max_length=12000
            )

        self.assertEqual(result, long_context)
        gemma_mock.assert_awaited_once()   
if __name__ == "__main__":
    asyncio.run(main())
    asyncio.run(test_connection_failure())

