import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.search_service import get_similar_chunks


# .env 파일의 내용을 환경변수로 불러옴
load_dotenv()
# os.getenv를 통해 안전하게 키를 가져옴
api_key = os.getenv("OPENAI_API_KEY")
# 클라이언트를 생성할 때 변수를 넣어줌.
client = OpenAI(api_key=api_key)

def ask_saha_ai(user_question: str):
    # DB에서 관련 정보 7개 찾아오기
    relevant_chunks = get_similar_chunks(user_question, top_k=7)
    
    # 참고할 본문 데이터 합치기
    context_text = "\n\n".join([
        f"출처: {c.title} (URL: {c.url})\n내용: {c.chunk_text}" 
        for c in relevant_chunks
    ])

    # 3. GPT에게 페르소나와 컨텍스트 부여
    messages = [
        {
            "role": "system", 
            "content": (
            "너는 부산 사하구청의 친절한 AI 상담사 '사하챗봇'이야. "
            "반드시 아래 제공된 [참고 정보]를 바탕으로 구민에게 도움이 되는 답변을 해줘. "
            "참고 정보에는 민원 안내, 구청 이용 방법, 공지사항 등이 포함되어 있어. " # 범위 확장
            "만약 참고 정보에 질문과 관련된 내용이 전혀 없다면, '죄송하지만 해당 정보에 대한 내용을 찾을 수 없습니다. 구체적인 사항은 사하구청 대표번호(051-220-4000)로 문의해 주세요.'라고 답해줘."
        )
        },
        {"role": "user", "content": f"[참고 정보]:\n{context_text}\n\n[질문]: {user_question}"}
    ]

    # 4. 답변 생성
    response = client.chat.completions.create(
        model="gpt-4o",  # 또는 gpt-3.5-turbo
        messages=messages,
        temperature=0.2 # 정확도를 위해 낮게 설정
    )

    return response.choices[0].message.content

if __name__ == "__main__":
    # 아까 검색 결과에 나왔던 '전자민원' 관련 질문으로 테스트
    q = "지방세 납부 하려면 어떻게 해야해?" 
    print(f"\n💬 질문: {q}")
    print("-" * 30)
    print(ask_saha_ai(q))