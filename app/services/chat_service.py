import os
import re
from dotenv import load_dotenv
from openai import OpenAI
from app.services.search_service import get_similar_chunks
from typing import List, Dict
import json
# openAI API
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

async def ask_saha_ai_stream(user_question: str, history: List[Dict[str, str]] = None):
    if history is None:
        history = []
    #==================================================================
    # [1] 쿼리 재작성: 과거 이력이 존재할 경우, 현재 질문의 대명사를 명확한 단어로 치환 
    #==================================================================
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

    #==================================================================
    # [1] RAG 문서 기반 파일첨부 기능 정규식 링크 수집 (일반 민원 서식용 - 순수하게 다 받아줌)
    #==================================================================
    
    # 하이브리드로 고도화된 스크립트 호출 (상위 3개 가져오기)
    relevant_chunks = get_similar_chunks(refined_question, top_k=3)
    
    # 디버깅 로그출력
    attached_files = []
    
    print(f"📦 DEBUG: get_similar_chunks가 물어온 문서 개수 = {len(relevant_chunks)}개")

    admin_stop_words = ["발급", "서류", "필요", "신청", "준비", "방법", "안내", "증명서", "확인", "신고", "처리", "절차", "비용"]
    
    # 쿼리에서 조사를 떼고, 행정 공통어를 제외한 '진짜 핵심 명사'만 남깁니다.
    query_keywords = [
        w for w in refined_question.split() 
        if len(w) > 1 and w not in admin_stop_words
    ]
    for i, c in enumerate(relevant_chunks):
        if i > 0:
            print(f" 🎯 1등 문서 검사 완료. 루프를 종료합니다.")
            break
        p_type = getattr(c, 'page_type', '')
        p_type_str = str(p_type) if p_type is not None else ''
        chunk_title = getattr(c, 'title', '무제')
        
        print(f"   [{i+1}등 문서] 제목: {chunk_title}, page_type: {p_type_str}")
        
        # page_type이 민원/서식 관련일 경우에만 링크 수집
        if any(t in p_type_str for t in ["민원", "civil", "서식", "form"]):
            # 쿼리에서 조사를 떼고, 행정 공통어를 제외한 '진짜 핵심 명사'만
            keywords = [
                w for w in refined_question.split() 
                if len(w) > 1 and w not in admin_stop_words
            ]
            
            is_doc_relevant = any(kw in chunk_title or kw in c.chunk_text for kw in keywords)
            
            if not is_doc_relevant:
                continue
            
            # 제목이 질문과 관련 없으면, 그 문서의 링크는 긁지 않음!
            if not is_doc_relevant:
                print(f" 🚫 [필터링 제외] 문서 제목이 질문과 무관: {chunk_title}")
                continue
            
            # chunk_text 내의 마크다운 링크 추출
            link_pattern = r'\[((?:\[[^\]]+\]|[^\]])+)\]\((https?://[^\)]+|/[^\)]+)\)'
            matches = re.findall(link_pattern, c.chunk_text)
            
            print(f"   👉 정규식 검색 결과 발견된 링크 개수: {len(matches)}개")
            
            for name, url in matches:
                if "saha.go.kr" in url:
                    if not any(f['file_url'] == url for f in attached_files):
                        attached_files.append({
                            "file_name": name.strip(),
                            "file_url": url.strip()
                        })
                        print(f" 파일 수집 성공 (필터링 통과): {name.strip()} -> {url.strip()}")

            if len(attached_files) > 0:
                print(f" 🎯 1등(또는 상위) 문서에서 파일 발견! 추가 탐색 중단.")
                break    

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
            "3. 큰 주제나 단계(Step)를 나눌 때는 '### 📍 1. 신청 방법' 처럼 위의 내용과 명확히 분리하고, 엔터는 한번만 쳐줘.\n"
            "4. 구비서류나 체크리스트를 나열할 때는 아래 예시처럼 항목당 딱 한 줄씩 깔끔하게 리스트로 작성해줘.\n"
            "   (예시)\n"
            "   - 🪪 **신분증**: 주민등록증, 운전면허증 등\n"
            "   - 📸 **여권용 컬러 사진 2매**: 최근 6개월 이내 촬영 (3.5cm × 4.5cm)\n"
            "5. 소제목(예: **수수료**, **주의사항**)에 볼드체 처리를 해줘.\n"
            "6. 정보가 부족하거나 개별 확인이 필요한 경우, 행정복지센터나 구청 관련 부서 연락처를 안내하며 친절하게 유도해줘.\n\n"
            "7. [★부서 및 연락처 안내] 참고 정보(Context) 본문 안에 담당 부서(과) 이름이나 전화번호가 포함되어 있다면, 답변 말미에 반드시 '📞 **담당 부서 안내**' 섹션을 만들어 따로 명시해줘. 없으면 그냥 없다고 해줘.\n"
            "8. [★정보 출처 명시] 구민들이 신뢰할 수 있도록, 제공된 참고 정보의 '출처'와 'URL'을 기반으로 답변 맨 마지막 줄에 '🔗 **관련 정보 링크**' 형태로 마크다운 링크를 제공해줘.\n"
            "9. [★파일 링크 금지] 답변에 첨부파일 이름을 언급할 때 절대 [파일명](URL) 같은 마크다운 하이퍼링크를 쓰지 말고, 그냥 텍스트로만 '파일명'을 적어줘.\n\n"
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
        temperature=0.2,
        stream=True # 스트리밍 모드 활성화 글자가 콸콸콸~~
    )
    # 실시간 텍스트 전송 및 답변 누적
    gpt_answer_accumulator = "" # 물을 받을 빈 바가지 준비
    # 한 글자씩 떨어지는 물방울(chunk)을 받아서 프론트로 넘김
    
    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            # print(f"DEBUG: 스트리밍 조각 생성됨: {content}") # 스트리밍 되는지 확인용
            gpt_answer_accumulator += content # 바가지에 물(텍스트) 모으기
            yield json.dumps({'type': 'text', 'content': content}) # 프론트로 즉시 발송
            
    #----------gpt 답변 생성 끝난 시점--------------
    
    #==================================================================
    # [2] 여권 pdf 파일 강제 첨부 로직 (rag로 수집되지 않는 여권 pdf 파일은 로컬에서 강제 첨부)
    #==================================================================
    # 여권 관련 pdf 파일이 저장된 로컬 경로
    pdf_dir = "data/passport_pdfs"
    # 지정한 폴더가 실제로 존재할 때만 파일 자동 매칭
    if os.path.exists(pdf_dir):
        all_local_files = os.listdir(pdf_dir)
    
        # 1. 여권 관련 질문이 들어왔을 때만 이 로컬 스캔 엔진을 개방
        if "여권" in user_question or (refined_question and "여권" in refined_question):
            
            for file_name_with_ext in all_local_files:
                # 확장자를 뗀 순수 파일명 추출 (예: '여권발급신청서', '여권분실신고서')
                pure_file_name, ext = os.path.splitext(file_name_with_ext)
                if ext.lower() == '.pdf':
                    is_matched = False
                    # 1. 파일명에서 특수문자/공백 제거하여 검색어 생성
                    search_name = re.escape(pure_file_name.replace(" ", ""))
                    #  본문에서 공백 제거 후 검색, 방금 위에서 조립 완료한 gpt_answer_accumulator 사용!
                    clean_gpt_answer = gpt_answer_accumulator.replace(" ", "")
                    
                    # 법정대리인동의서 예외 처리 ("법정대리인 또는 보호자 동의서" 형태로 흩어진 경우 방어)
                    if pure_file_name == "법정대리인동의서":
                        if "법정대리인" in gpt_answer_accumulator and "동의서" in gpt_answer_accumulator:
                            is_matched = True
                            
                   # 그 외 일반 파일들 
                    else:
                        # 💡 핵심 수정: 단순 in 연산자 대신 정규식으로 단어 단위 매칭
                        # \b는 단어의 시작과 끝 경계를 의미합니다. 
                        # 이렇게 하면 "여권발급신청서"라는 정확한 단어가 있을 때만 매칭됩니다.
                        
                        
                        # 3. 검색어와 정확히 일치하는 패턴이 있는지 확인
                        if re.search(search_name, clean_gpt_answer):
                            is_matched = True       
                    
                    # 최종 검증을 통과한 파일만 첨부
                    if is_matched:
                        file_url = f"/download/passport_pdfs/{file_name_with_ext}"
                        
                        # 중복 수집 방지 체크 후 최종 바구니에 담기
                        if not any(f['file_url'] == file_url for f in attached_files):
                            attached_files.append({
                                "file_name": file_name_with_ext,
                                "file_url": file_url
                            })
                            print(f" 📁 [로컬 첨부 성공] 본문 언급 확인되어 첨부 완료: {file_name_with_ext}")
    
    
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

    #========================================================================
    # 최종 답변 및 첨부 파일 리스트 리턴
    #========================================================================
    yield json.dumps({'type': 'files', 'content': attached_files})
    # 추가: 프론트엔드에 끝났음을 명확히 알림
    yield json.dumps({'type': 'done'})

    