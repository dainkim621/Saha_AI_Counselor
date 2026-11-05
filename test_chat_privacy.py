
import unittest
from unittest.mock import AsyncMock, patch
from types import SimpleNamespace
from app.services.chat_service import ask_saha_ai_stream
from app.secure.regex_filter import PrivacyBlocked


class TestChatPrivacy(unittest.IsolatedAsyncioTestCase):

    async def run_chat(self, question, history=None):
        return [
            event
            async for event in ask_saha_ai_stream(
                question, history=history
            )
        ]

    async def test_rrn_blocked_before_external_api(self):
        """주민등록번호 형태의 입력은 외부 API 호출 전에 차단"""

        with patch(
            "app.secure.privacy_guard.detect_personal_info",
            new_callable=AsyncMock,
            return_value=[]
        ) as gemma_mock, patch(
            "app.services.chat_service.client"
        ) as openai_mock, patch(
            "app.services.chat_service.get_similar_chunks"
        ) as search_mock:

            events = await self.run_chat(
                "주민번호 990101-1234567로 신청할 수 있나요?"
            )

            openai_mock.chat.completions.create.assert_not_called()
            search_mock.assert_not_called()
            gemma_mock.assert_not_awaited()

            self.assertTrue(
                any("개인정보" in event for event in events)
            )

    async def test_gemma_failure_blocks_external_api(self):
        """Gemma 연결 실패 시 외부 API 호출 금지"""

        with patch(
            "app.secure.privacy_guard.detect_personal_info",
            new_callable=AsyncMock,
            side_effect=ConnectionError("Mock Gemma offline")
        ), patch(
            "app.services.chat_service.client"
        ) as openai_mock, patch(
            "app.services.chat_service.get_similar_chunks"
        ) as search_mock:

            events = await self.run_chat(
                "대형폐기물 신청 방법 알려줘"
            )

            openai_mock.chat.completions.create.assert_not_called()
            search_mock.assert_not_called()

            self.assertTrue(
                any("검사할 수 없습니다" in event for event in events)
            )

    async def test_private_history_blocks_external_api(self):
        """대화 이력에 민감정보가 있으면 외부 API 호출 금지"""

        async def fake_gemma(text):
            if "가상계좌" in text:
                return [{
                    "text": "가상계좌",
                    "type": "ACCOUNT"
                }]
            return []

        with patch(
            "app.secure.privacy_guard.detect_personal_info",
            new_callable=AsyncMock,
            side_effect=fake_gemma
        ), patch(
            "app.services.chat_service.client"
        ) as openai_mock, patch(
            "app.services.chat_service.get_similar_chunks"
        ) as search_mock:

            events = await self.run_chat(
                "그 신청 방법 알려줘",
                history=[
                    {
                        "role": "user",
                        "content": "제 가상계좌 관련 문의예요"
                    }
                ]
            )

            openai_mock.chat.completions.create.assert_not_called()
            search_mock.assert_not_called()

            self.assertTrue(
                any("개인정보" in event for event in events)
            )

    async def test_phone_masked_before_external_api(self):
        """전화번호를 마스킹한 뒤 외부 GPT에 전달하는지 검사"""

        from types import SimpleNamespace

        fake_response = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    delta=SimpleNamespace(content="신청 방법을 안내합니다.")
                )
            ]
        )

        with patch(
            "app.secure.privacy_guard.detect_personal_info",
            new_callable=AsyncMock,
            return_value=[]
        ), patch(
            "app.services.chat_service.client"
        ) as openai_mock, patch(
            "app.services.chat_service.get_similar_chunks",
            return_value=(
                [
                    SimpleNamespace(
                        title="대형폐기물 배출 안내",
                        url="https://www.saha.go.kr",
                        chunk_text="대형폐기물은 신고 후 배출할 수 있습니다.",
                        score=0.95,
                        page_type="일반 안내"
                    )
                ],
                []
            )
        ) as search_mock, patch(
            "app.services.chat_service.SessionLocal"
        ) as db_mock:
            # 테스트 DB에는 기존 FAQ 기록이 없는 것으로 설정
            db_mock.return_value.query.return_value \
                .filter.return_value \
                .order_by.return_value \
                .first.return_value = None
            openai_mock.chat.completions.create.side_effect = [
                iter([fake_response]),
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content="소파 폐기 신청 방법"
                            )
                        )
                    ]
                ),
                SimpleNamespace(
                    choices=[
                        SimpleNamespace(
                            message=SimpleNamespace(
                                content='{"success":true,"category":"NONE","reason":""}'
                            )
                        )
                    ]
                )
            ]

            await self.run_chat(
                "제 번호는 010-1234-5678입니다. 소파 버리는 방법 알려줘"
            )

            # 첫 번째 GPT 호출은 답변 생성
            first_call = openai_mock.chat.completions.create.call_args_list[0]
            messages = first_call.kwargs["messages"]

            user_message = messages[-1]["content"]

            self.assertIn("[전화번호]", user_message)
            self.assertNotIn("010-1234-5678", user_message)
            
            # 검색 함수에 개인정보가 제거된 질문이 전달됐는지 확인
            search_mock.assert_called_once()

            search_query = search_mock.call_args.args[0]

            self.assertIn("[전화번호]", search_query)

            self.assertNotIn(
                "010-1234-5678",
                search_query,
                "검색용 임베딩에 원본 전화번호가 전달될 위험이 있습니다."
            )

            # 모든 외부 GPT 호출의 메시지에 원본 전화번호가 없는지 검사
            for call in openai_mock.chat.completions.create.call_args_list:
                messages = call.kwargs.get("messages", [])

                for message in messages:
                    content = message.get("content", "")

                    self.assertNotIn(
                        "010-1234-5678",
                        str(content),
                        "외부 GPT 요청에 원본 전화번호가 포함되었습니다."
                    )

            db_mock.assert_called_once()
            # DB 저장 함수가 호출되었는지 확인
            db_mock.return_value.add.assert_called_once()
            db_mock.return_value.commit.assert_called_once()

            # 개인정보 검사 실패로 저장이 취소되지 않았는지 확인
            db_mock.return_value.rollback.assert_not_called()

if __name__ == "__main__":
    unittest.main()
