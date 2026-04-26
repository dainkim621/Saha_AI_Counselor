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
    # DB에서 관련 정보 3개 찾아오기
    relevant_chunks = get_similar_chunks(user_question, top_k=3)
    
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
                "너는 부산 사하구청의 친절한 AI 상담사 '사하챗봇'야. "
                "반드시 아래 제공된 [참고 정보]만을 바탕으로 답변해줘. "
                "만약 참고 정보에 답이 없다면, '죄송하지만 해당 정보는 현재 공지사항에서 찾을 수 없습니다.'라고 답해줘."
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
    q = "전자민원 서비스에 대해 설명해줘" 
    print(f"\n💬 질문: {q}")
    print("-" * 30)
    print(ask_saha_ai(q))