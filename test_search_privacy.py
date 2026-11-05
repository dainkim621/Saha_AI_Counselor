import unittest
from unittest.mock import patch, AsyncMock
from types import SimpleNamespace

from app.services.search_service import get_similar_chunks


class TestSearchPrivacy(unittest.IsolatedAsyncioTestCase):

    async def test_masked_query_sent_to_embedding(self):
        """마스킹된 검색어가 임베딩 API에 그대로 전달되는지 검사"""

        safe_query = "제 번호는 [전화번호]입니다. 소파 버리는 방법 알려줘"

        fake_embedding_response = SimpleNamespace(
            data=[
                SimpleNamespace(
                    embedding=[0.1, 0.2, 0.3]
                )
            ]
        )

        with patch(
            "app.services.search_service.client"
        ) as openai_mock, patch(
            "app.secure.privacy_guard.detect_personal_info",
            new_callable=AsyncMock,
            return_value=[]
        ), patch(
            "app.services.search_service.SessionLocal"
        ) as db_mock:

            # 실제 OpenAI API 호출 방지
            openai_mock.embeddings.create.return_value = (
                fake_embedding_response
            )

            # 실제 DB 검색 방지
            db_mock.return_value.query.return_value \
                .order_by.return_value \
                .limit.return_value \
                .all.return_value = []

            db_mock.return_value.query.return_value \
                .filter.return_value \
                .limit.return_value \
                .all.return_value = []

            # 검색 함수 실행
            results, embedding = await get_similar_chunks(safe_query)

            # 임베딩 API 호출 확인
            openai_mock.embeddings.create.assert_called_once_with(
                input=safe_query,
                model="text-embedding-3-small"
            )

            # 원본 전화번호가 전송되지 않았는지 확인
            sent_query = (
                openai_mock.embeddings.create.call_args.kwargs["input"]
            )

            self.assertNotIn(
                "010-1234-5678",
                sent_query
            )

            self.assertIn(
                "[전화번호]",
                sent_query
            )

            # 검색 결과 확인
            self.assertEqual(results, [])
            self.assertEqual(embedding, [0.1, 0.2, 0.3])

            # DB 연결 종료 확인
            db_mock.return_value.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()