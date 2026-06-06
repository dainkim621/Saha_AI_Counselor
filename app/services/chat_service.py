import os
from dotenv import load_dotenv
from openai import OpenAI
from app.services.search_service import get_similar_chunks
# 💡 [필수 추가] 파이썬 타입 지정을 위해 List와 Dict를 꼭 임포트해야 에러가 안 납니다!
from typing import List, Dict


# .env 파일의 내용을 환경변수로 불러옴
load_dotenv()
# os.getenv를 통해 안전하게 키를 가져옴
api_key = os.getenv("OPENAI_API_KEY")
# 클라이언트를 생성할 때 변수를 넣어줌.
client = OpenAI(api_key=api_key)


# 💡 [교정] history가 정상적으로 유입되도록 매개변수 구조를 완전히 고정합니다.
def ask_saha_ai(user_question: str, history: List[Dict[str, str]] = None):
    if history is None:
        history = []

    # 💡 [핵심 추가] 과거 이력이 존재할 경우, 현재 질문의 대명사를 명확한 단어로 치환 (Query Rewriting)
    refined_question = user_question
    if history:
        try:
            # 대화 이력을 참고하여 '그거'가 무엇인지 파악하는 압축 질문 생성용 prompt
            rewriter_messages = [
                {
                    "role": "system",
                    "content": (
                        "너는 사용자의 질문을 분석하여 RAG 검색에 최적화된 독립적인 검색용 쿼리로 재작성하는 전문가야. "
                        "이전 대화 기록을 바탕으로, 사용자의 최신 질문에 포함된 '그거', '거기', '이거' 등의 대명사를 명확한 행정 용어로 바꾸어 단 한 줄의 핵심 검색어로 재작성해줘. "
                        "설명은 빼고 오직 단 한 줄의 검색용 문장만 출력해야 해."
                    )
                }
            ]
            # 과거 이력 추가
            for chat in history:
                rewriter_messages.append({"role": chat["role"], "content": chat["content"]})
            
            # 현재 질문 추가
            rewriter_messages.append({"role": "user", "content": f"이 질문을 명확한 검색어로 바꿔줘: {user_question}"})
            
            # GPT에게 쿼리 재작성 요청
            rewrite_response = client.chat.completions.create(
                model="gpt-4o-mini", # 가벼운 모델로 빠르게 처리
                messages=rewriter_messages,
                temperature=0.0
            )
            refined_question = rewrite_response.choices[0].message.content.strip()
            print(f"🔍 쿼리 재작성 완료: '{user_question}' ➔ '{refined_question}'")
        except Exception as e:
            print(f"⚠️ 쿼리 재작성 실패(기본 질문 사용): {e}")
            refined_question = user_question

    # 💡 [변경] 원본 질문 대신, 대명사가 교정된 'refined_question'으로 DB 검색을 수행합니다!
    relevant_chunks = get_similar_chunks(refined_question, top_k=7)
    
    # 참고할 본문 데이터 합치기
    context_text = "\n\n".join([
        f"출처: {c.title} (URL: {c.url})\n내용: {c.chunk_text}" 
        for c in relevant_chunks
    ])

    # (이하 시스템 프롬프트 조립 및 최종 gpt-4o 호출 코드는 기존과 동일...)
    # 단, 최종 질문에는 유저가 입력한 원본 문장(user_question)을 넣어주어야 대화가 자연스럽습니다.
    messages = [
        {
            "role": "system", 
            "content": (
            "너는 부산 사하구청의 친절한 AI 상담사 '고우니'이야."
            "[역할 및 출력 지침]"
            "너는 사하구청 행정 안내 AI 챗봇 '고우니'야. 구민의 질문에 Context를 바탕으로 답변해줘."

            "반드시 아래 제공된 [참고 정보]를 바탕으로 구민에게 도움이 되는 답변을 해줘. "
            "참고 정보에는 민원 안내, 구청 이용 방법, 공지사항 등이 포함되어 있어. " # 범위 확장

            "제공된 [참고 정보]를 최우선으로 바탕으로 답변하되, 참고 정보에 구체적인 서류 목록이 누락되어 있다면 이전 대화 맥락(기초생활수급자 선정 기준 등)을 고려하여 구민이 동 주민센터나 구청 복지 부서에 문의해야 함을 친절하게 안내해줘."            f"--- [중요] 이번 질문에 대한 최신 참고 정보 ---\n"
            f"{context_text}\n"
            f"----------------------------------------"
            )
        }    
    ]
    for chat in history:
        messages.append({"role": chat["role"], "content": chat["content"]})
    
    # 사용자의 원본 질문 투입
    messages.append({"role": "user", "content": user_question})

    # 4. 답변 생성
    response = client.chat.completions.create(
        model="gpt-4o",  
        messages=messages,
        temperature=0.2 
    )
    return response.choices[0].message.content


if __name__ == "__main__":
    # 아까 검색 결과에 나왔던 '전자민원' 관련 질문으로 테스트
    q = "주민등록등·초본, 전입세대열람 발급하려면 어떻게 해?" 
    print(f"\n💬 질문: {q}")
    print("-" * 30)
    print(ask_saha_ai(q))
    
    