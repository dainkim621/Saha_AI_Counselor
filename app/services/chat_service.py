import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from app.services.search_service import get_similar_chunks
from typing import List, Dict


# .env 파일의 내용을 환경변수로 불러옴
load_dotenv()
# os.getenv를 통해 안전하게 키를 가져옴
api_key = os.getenv("OPENAI_API_KEY")
# 클라이언트를 생성할 때 변수를 넣어줌.
client = OpenAI(api_key=api_key)

def ask_saha_ai(user_question: str, history: List[Dict[str, str]] = None):
    if history is None:
        history = []

    # 과거 이력이 존재할 경우, 현재 질문의 대명사를 명확한 단어로 치환 (쿼리 재작성)
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

    # 하이브리드로 고도화된 스크립트 호출 (상위 5개 가져오기)
    relevant_chunks = get_similar_chunks(refined_question, top_k=5)
    
    # 디버깅 로그출력
    attached_files = []
    
    print(f"📦 DEBUG: get_similar_chunks가 물어온 문서 개수 = {len(relevant_chunks)}개")

    for i, c in enumerate(relevant_chunks):
        # if i > 0: 
        #     break # 1등 문서만 검사하고 반복문을 완전히 종료 (또는 점수 기준 2등까지면 i > 1)
        p_type = getattr(c, 'page_type', '')
        p_type_str = str(p_type) if p_type is not None else ''
        
        
        print(f"   [{i+1}등 문서] 제목: {getattr(c, 'title', '무제')}, page_type: {p_type_str}")
        
        # 한글, 영문, 혹은 공백 유무에 상관없이 관련 단어가 감지되면 무조건 개방
        if any(t in p_type_str for t in ["민원", "civil", "passport", "서식", "여권", "필요", "준비", "서류", "신청서", "서식", "양식", "발급"]):
            
            # chunk_text 내의 마크다운 링크 추출
            link_pattern = r'\[((?:\[[^\]]+\]|[^\]])+)\]\((https?://[^\)]+|/[^\)]+)\)'
            matches = re.findall(link_pattern, c.chunk_text)
            
            print(f"   👉 정규식 검색 결과 발견된 링크 개수: {len(matches)}개")
            
            for name, url in matches:
                if "saha.go.kr" in url or "/download/" in url:
                    # 발견된 파일 이름이 유저 질문(또는 재작성 쿼리)의 핵심 키워드를 포함하는지 검사
                    # 예: 질문이 '가족관계'면 파일명에 '가족'이 들어가거나, 청크 제목(c.title)에 '가족'이 있어야 함
                    # 유저 질문에서 조사 등을 뗀 핵심 명사 위주로 매칭하면 좋음.
                    
                    # 질문이나 재작성 쿼리에서 핵심 단어 추출 (간단하게 단어 포함 여부 체크)
                    query_keywords = [w for w in refined_question.split() if len(w) > 1]
                    
                    # 파일 이름이나 문서 제목에 질문의 핵심 키워드가 하나라도 겹치는지 확인
                    is_relevant_file = any(kw in name or kw in getattr(c, 'title', '') for kw in query_keywords)
                    
                    # 만약 여권 관련 룰이 켜져있거나, 키워드가 매칭될 때만 최종 수집
                    if is_relevant_file or "passport" in p_type_str:
                        if not any(f['file_url'] == url for f in attached_files):
                            attached_files.append({
                                "file_name": name.strip(),
                                "file_url": url.strip()
                            })
                            print(f" 파일 수집 성공 (필터링 통과): {name.strip()} -> {url.strip()}")
                

    print(f"🎯 최종 프론트로 넘겨줄 attached_files 수집본: {attached_files}")
    
    # 참고할 본문 데이터 합치기
    context_text = "\n\n".join([
        f"출처: {c.title} (URL: {c.url})\n내용: {c.chunk_text}" 
        for c in relevant_chunks
    ])
    
    # GPT 프롬프트
    messages = [
        {
            "role": "system", 
            "content": (
            "너는 부산 사하구청의 친절하고 깔끔한 AI 상담사 '고우니'이야. 구민의 질문에 예의바르게 답변해줘야해."
            "[역할 및 출력 지침]\n"
            "1. 구민의 질문에 제공된 [참고 정보](Context)를 바탕으로 정확하게 답변해줘.\n"
            "2. [핵심] 큰 주제나 소제목(###)이 바뀔 때만 줄바꿈(엔터 2번)을 해주고, 같은 항목 안의 서술형 문장들은 한 줄로 부드럽게 이어 써줘.\n"
            "3. 정보를 나열할 때는 반드시 마크다운 리스트 문법('- ')을 사용하되, 리스트 기호 하나당 딱 한 줄씩만 깔끔하게 작성해줘.\n"
            "4. 소제목이나 강조하고 싶은 핵심 단어(예: **수수료**, **준비물**)에만 볼드체를 쓰고, 문장 전체에 남발하지 마.\n"
            "5. 정보가 부족하거나 답변이 어려울 경우, 행정복지센터(동 주민센터)나 구청 관련 부서에 문의하도록 친절하게 유도해줘.\n\n"
            "6. 구민들이 알아보기 쉽게 답변을 구조화해서 보여줘."
            f"--- [중요] 이번 질문에 대한 최신 참고 정보 ---\n"
            f"{context_text}\n"
            f"----------------------------------------"
            )
        }    
    ]
    for chat in history:
        messages.append({"role": chat["role"], "content": chat["content"]})
    
    # 사용자의 원본 질문 투입
    messages.append({"role": "user", "content": user_question})

    # 답변 생성
    response = client.chat.completions.create(
        model="gpt-4o",  
        messages=messages,
        temperature=0.2 
    )
    gpt_answer = response.choices[0].message.content
    # 1. 로컬에 저장되어 있는 실제 서식 파일 목록 정의
    # (실제 /data/passport_pdfs/ 안의 파일명 넣기)(여권 pdf들은 수가 적고, 중요도가 높아서 ok)
    local_files = {
        "여권발급신청서": "/download/passport_pdfs/여권발급신청서.pdf",
        "법정대리인동의서": "/download/passport_pdfs/법정대리인동의서.pdf",
        "여권분실신고서": "/download/passport_pdfs/여권분실신고서.pdf",
        "긴급여권발급신청사유서": "/download/passport_pdfs/긴급여권발급신청사유서.pdf"
    }

    # 2. GPT의 답변 내용(gpt_answer)이나 유저 질문에 파일 이름이 언급되었는지 검사
    for file_name, file_url in local_files.items():
        # 답변 멘트에 "여권발급신청서"가 포함되어 있거나, 유저가 질문에 언급했다면
        if file_name in gpt_answer or file_name in user_question:
            # 중복 체크 후 attached_files에 강제 주입
            if not any(f['file_url'] == file_url for f in attached_files):
                attached_files.append({
                    "file_name": f"{file_name}.pdf",
                    "file_url": file_url
                })
                print(f"[로컬 파일 매칭] {file_name} 강제 첨부 성공")
    
    #-----------------------
    # 첨부 파일 버튼 중복 제거
    unique_files = []
    seen_urls = set()
    seen_names = set() # 파일 이름 중복도 감시하기 위해 추가 (정규식이 긁어온 url이 미세하게 바뀌어서 중복제거가 잘 안되는 것 같음.)
    
    for file_info in attached_files:
        # 양끝 공백을 완전히 깎아내고 소문자 변환(혹시 모를 영문 주소 대비) 처리
        url = file_info.get('file_url', '').strip()
        name = file_info.get('file_name', '').strip()
        
        # URL과 파일 이름 둘 다 기존에 등록된 적이 없을 때만 통과!
        if url not in seen_urls and name not in seen_names:
            seen_urls.add(url)
            seen_names.add(name)
            unique_files.append(file_info)
        else:
            print(f"✂️ [중복 차단 완료] 겹치는 파일 발견되어 제거함: {name}")
            
    # 정제된 유일한 파일 리스트로 교체
    attached_files = unique_files
    #-----------------------
    
    return {
        "answer": gpt_answer,
        "files": attached_files
    }


# 테스트용 코드
if __name__ == "__main__":
    # 아까 검색 결과에 나왔던 '전자민원' 관련 질문으로 테스트
    q = "주민등록등·초본, 전입세대열람 발급하려면 어떻게 해?" 
    print(f"\n💬 질문: {q}")
    print("-" * 30)
    print(ask_saha_ai(q))
    
    