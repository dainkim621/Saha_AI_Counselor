import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from app.services.search_service import get_similar_chunks
from typing import List, Dict

# openAI API
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
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

    #==================================================================
    # [1] RAG 문서 기반 파일첨부 기능 정규식 링크 수집 (일반 민원 서식용 - 순수하게 다 받아줌)
    #==================================================================
    # < 1단계 > 유저 질문 및 재작성 쿼리 단어 추출
    # 의미 없는 1글자 단어(조사 등)를 걸러내고 핵심 명사 위주로 세트(Set)를 만듬.
    current_words = set([w for w in user_question.split() if len(w) > 1])
    refined_words = set([w for w in refined_question.split() if len(w) > 1]) if refined_question else set()
    # 두 쿼리의 단어를 모두 합쳐 '최종 검사 키워드 바구니' 생성
    final_target_words = current_words | refined_words
    
    for i, c in enumerate(relevant_chunks):
        p_type = getattr(c, 'page_type', '')
        p_type_str = str(p_type) if p_type is not None else ''
        chunk_title = getattr(c, 'title', '무제')
        
        print(f"   [{i+1}등 문서] 제목: {chunk_title}, page_type: {p_type_str}")
        
        # 한글, 영문, 혹은 공백 유무에 상관없이 관련 단어가 감지되면 무조건 개방
        if any(t in p_type_str for t in ["민원", "civil", "서식", "여권", "필요", "준비", "서류", "신청서", "서식", "양식", "발급"]):
            
            # RAG가 끼워 파는 엉뚱한 문서 쳐내기 (제목 연관성 검사)
            # 예: 유저 질문은 "가족관계증명서"인데 3등 문서 제목이 "출입국 사실증명서"인 경우
            # final_target_words에 '출입국'이 없으므로 False가 되어 억울한 오탐을 완벽히 차단
            is_title_relevant = any(kw in chunk_title for kw in final_target_words)
            
            # 문서 제목이 유저 질문 문맥과 일치할 때만 링크 추출 진행
            if is_title_relevant:
                # chunk_text 내의 마크다운 링크 추출
                link_pattern = r'\[((?:\[[^\]]+\]|[^\]])+)\]\((https?://[^\)]+|/[^\)]+)\)'
                matches = re.findall(link_pattern, c.chunk_text)
            
                print(f"   👉 정규식 검색 결과 발견된 링크 개수: {len(matches)}개")
            
                for name, url in matches:
                    if "saha.go.kr" in url or "/download/" in url:
                        clean_name = name.strip()
                        clean_url = url.strip()
                        
                        # 💡 일반 민원은 본문에 링크가 꽂혀있으므로 중복만 아니면 100% 안전하게 바구니에 다 담아줍니다!
                        if not any(f['file_url'] == clean_url for f in attached_files):
                            attached_files.append({
                                "file_name": clean_name,
                                "file_url": clean_url
                            })
                            print(f" 📄 [RAG 본문 수집 성공]: {clean_name}")
                

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
            "1. 구민의 질문에 제공된 [참고 정보](Context)를 바탕으로 핵심만 정확하게 답변해줘.\n"
            "2. [시각적 구조화] 절대 긴 줄글로만 나열하지 말고, 구민이 한눈에 정보를 파악할 수 있도록 적절한 이모지(아이콘)과 글머리 기호('-')를 적극적으로 사용해줘.\n"
            "3. 큰 주제나 단계(Step)를 나눌 때는 '### 📍 1. 신청 방법' 처럼 소제목을 명확히 분리하고 줄바꿈을 해줘.\n"
            "4. 구비서류나 체크리스트를 나열할 때는 아래 예시처럼 항목당 딱 한 줄씩 깔끔하게 리스트로 작성해줘.\n"
            "   (예시)\n"
            "   - 🪪 **신분증**: 주민등록증, 운전면허증 등\n"
            "   - 📸 **여권용 컬러 사진 2매**: 최근 6개월 이내 촬영 (3.5cm × 4.5cm)\n"
            "5. 소제목이나 중요 정보나 강조 단어(예: **수수료**, **주의사항**)는 볼드체 처리를 해주고, 문장 전체에 남발하지는 마.\n"
            "6. 정보가 부족하거나 개별 확인이 필요한 경우, 행정복지센터나 구청 관련 부서 연락처를 안내하며 친절하게 유도해줘.\n\n"
            "7. [★부서 및 연락처 안내] 참고 정보(Context) 본문 안에 담당 부서(과) 이름이나 전화번호가 포함되어 있다면, 답변 말미에 반드시 '📞 **담당 부서 안내**' 섹션을 만들어 따로 명시해줘. 없으면 그냥 없다고 해줘.\n"
            "8. [★정보 출처 명시] 구민들이 신뢰할 수 있도록, 제공된 참고 정보의 '출처'와 'URL'을 기반으로 답변 맨 마지막 줄에 '🔗 **관련 정보 링크**' 형태로 마크다운 링크를 제공해줘.\n"
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
    
    
    #==================================================================
    # [2] 여권 pdf 파일 강제 첨부 로직 (rag로 수집되지 않는 여권 pdf 파일은 로컬에서 강제 첨부)
    #==================================================================
    # 여권 관련 pdf 파일이 저장된 로컬 경로
    pdf_dir = "data/passport_pdfs"
    
    # 지정한 폴더가 실제로 존재할 때만 파일 자동 매칭
    if os.path.exists(pdf_dir):
        # 폴더 안의 모든 파일 목록을 리스트로 긁어옴 (예: ['여권발급신청서.pdf', '새로운서식.pdf'])
        all_local_files = os.listdir(pdf_dir)
    
        # 1. 여권 관련 질문이 들어왔을 때만 이 로컬 스캔 엔진을 개방
        if "여권" in user_question or (refined_question and "여권" in refined_question):
            
            for file_name_with_ext in all_local_files:
                # 확장자를 뗀 순수 파일명 추출 (예: '여권발급신청서', '여권분실신고서')
                pure_file_name, ext = os.path.splitext(file_name_with_ext)
        
                if ext.lower() == '.pdf':
                    
                
                    # 2. GPT가 최종적으로 만들어낸 답변 본문(gpt_answer) 안에 
                    # 로컬 파일 이름이 글자 그대로 포함되어 있는지 검사함. 
                    # 예: GPT가 본문에 "여권분실신고서.pdf 파일을 다운로드하세요"라고 적었다면 매칭 성공
                    if pure_file_name in gpt_answer:
                        file_url = f"/download/passport_pdfs/{file_name_with_ext}"
                        
                        # 중복 수집 방지 체크 후 최종 바구니에 담기
                        if not any(f['file_url'] == file_url for f in attached_files):
                            attached_files.append({
                                "file_name": file_name_with_ext,
                                "file_url": file_url
                            })
                            print(f" 📁 [챗봇 답변 매칭 성공] 본문 언급 확인되어 첨부 완료: {file_name_with_ext}")
    
    
    #===========================================================================
    # [3] 첨부 파일 버튼 중복 제거 (여권 pdf가 rag로도 수집되고, 로컬에서도 강제 첨부되는 경우)
    #===========================================================================
    unique_files = []
    seen_urls = set()
    seen_names = set() # 파일 이름 중복도 감시하기 위해 추가 (정규식이 긁어온 url이 미세하게 바뀌어서 중복제거가 잘 안되는 것 같음.)
    
    for file_info in attached_files:
        # 양끝 공백을 없애고 소문자 변환(혹시 모를 영문 주소 대비) 처리
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
    
    # =========================================================================
    # GPT 답변 본문의 불필요한 파일 하이퍼링크 제거
    # =========================================================================
    # GPT가 [여권분실신고서.pdf](url) 형태로 뱉은 마크다운을 -> "여권분실신고서.pdf" 일반 텍스트로 바꿉니다.
    # (단, 외부 정보 안내 링크 같은 일반 웹사이트 http 하이퍼링크는 파괴되지 않고 살아남습니다!)
    gpt_answer = re.sub(r'\[([^\]]+\.(?:pdf|hwp|doc|docx))\]\([^\)]+\)', r'\1', gpt_answer)
    
    # 혹시 URL 쪽에 확장자가 있는 경우도 방어
    gpt_answer = re.sub(r'\[([^\]]+)\]\([^\)]+\.(?:pdf|hwp|doc|docx)\)', r'\1', gpt_answer)


    #=================================
    # 최종 답변 및 첨부 파일 리스트 리턴
    #=================================
    return {
        "answer": gpt_answer,
        "files": attached_files
    }


    