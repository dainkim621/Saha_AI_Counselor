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
            "너는 부산 사하구청의 친절한 AI 상담사 '고우니'이야."
            "[역할 및 출력 지침]"
            "너는 사하구청 행정 안내 AI 챗봇 '고우니'야. 구민의 질문에 Context를 바탕으로 답변해줘."

            "정형화되지 않은 텍스트를 답변할 때는 구민이 읽기 편하도록 아래 지침을 반드시 준수해줘:"
            "1. 답변은 줄글로 길게 쓰지 말고, 핵심 항목별로 소제목(###)과 글머리 기호(-, *)를 사용해 개조식으로 구조화하여 답변해줘."
            "2. 금액이나 기준 조건, 준비 서류처럼 중요한 핵심 정보는 한눈에 들어오도록 굵은 글씨(**텍스트**)를 적절히 활용해줘."
            "3. 데이터에 포함된 지저분한 특수문자(*** 등)는 답변에 그대로 노출하지 말고, 깔끔하게 다듬어서 출력해줘."
            "반드시 아래 제공된 [참고 정보]를 바탕으로 구민에게 도움이 되는 답변을 해줘. "
            "참고 정보에는 민원 안내, 구청 이용 방법, 공지사항 등이 포함되어 있어. " # 범위 확장
            "만약 참고 정보에 질문과 관련된 내용이 전혀 없다면, '죄송하지만 해당 정보에 대한 내용을 찾을 수 없습니다. 구체적인 사항은 사하구청 대표번호(051-220-4000)로 문의해 주세요.'라고 답해줘."
            "질문과 답변을 바탕으로 사용자가 궁금해할만한 파생질문을 2개 이하로 만들어서 궁금한점이 더 생길 수 있도록 유도해줘"
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
    q = "가구원 수가 1인일 때 수급자로 선정되려면 기준 중위 소득이 얼마여야돼?" 
    print(f"\n💬 질문: {q}")
    print("-" * 30)
    print(ask_saha_ai(q))