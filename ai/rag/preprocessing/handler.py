#예외처리나 하드코딩 있는 함수들 모아둔 파일임

import re

def check_merge_condition(unique_headings):
    """
    조건 분리: 현재 섹션이 병합 대상(요일별, 구역별, 월별 데이터 등)인지 판별하는 함수
    - 요일 단독 글자('월', '화' 등)
    - '구역' 또는 '동'으로 끝나는 소제목
    - '월'로 끝나는 숫자 소제목 (예: '1월', '12월')
     위의 조건에 해당하면 True를 반환하여 마스터 함수가 데이터를 모으도록 합니다.
    """
    if not unique_headings:
        return False
        
    last_heading = str(unique_headings[-1]).strip()
    
    # 정규식 대신 리스트/문자열 in 검사를 쓰면 더 직관적입니다.
    # 정확히 한 글자이면서 월~일 중 하나인지 검사
    if last_heading in ["월", "화", "수", "목", "금", "토", "일"]:
        return True
    
    # 확장:if문 추가해서 한 주제의 청크들을 전처리 단계에서 하나로 묶어주고 싶을 때, 여기서 조건을 추가하면 됨.
    # # 2. 구역 및 지역 패턴 ('~구역', '~동'으로 끝나는 경우)
    # if last_heading.endswith("구역") or last_heading.endswith("동"):
    #     return True
        
    # # 3. [확장] 월별 패턴 ('1월' ~ '12월' 처럼 숫자가 앞에 붙고 '월'로 끝나는 경우)
    # if last_heading.endswith("월") and last_heading[:-1].isdigit():
    #     return True
        
    return False


def build_merged_chunk_text(parent_path, grouped_items):
    """
    포맷 분리: 수집된 예외 그룹 데이터(요일, 구역 등)를 하나의 마크다운 텍스트 본문으로 조립하는 함수
    - 특정 텍스트('요일')를 강제하지 않고 들어온 키값 그대로 대괄호 안에 넣어 유연하게 대응합니다.
    """
    merged_body_lines = []
    for key, body in grouped_items:
        # 💡 요일 외에 다른 데이터가 들어와도 자연스럽게 매핑되도록 처리
        # 예: [월] -> [월요일] 보정 / [1구역] 이나 [1월]은 그대로 유지
        display_key = f"{key}요일" if key in ["월", "화", "수", "목", "금", "토", "일"] else key
        
        # 각 그룹별 본문 조립 (예: [월요일]\n재활용품...)
        merged_body_lines.append(f"[{display_key}]\n{body}")
        
    # 각 섹션 본문을 개행 두 번(\n\n)으로 구분하여 깔끔하게 결합
    clean_section_text = "\n\n".join(merged_body_lines)
    
    # 최종 마크다운 형태의 텍스트 반환
    return f"# {parent_path}\n{clean_section_text}"



    #            ┌─────────────────────────────┐
    #            │    Raw 크롤링 데이터 섹션     │
    #            └──────────────┬──────────────┘
    #                           │
    #            ┌──────────────▼──────────────┐
    #            │  check_merge_condition()    │ ◀── [새로운 예외는 여기만 수정!]
    #            └──────┬───────────────┬──────┘
    #                   │ (True)        │ (False)
    #                   │               │
    #  ┌────────────────▼──────┐        │
    #  │ weekly_groups에 차곡차곡│        │
    #  │   데이터 모으기 (대기)  │         │
    #  └────────────────┬──────┘        │
    #                   │               │
    #  ┌────────────────▼──────┐  ┌─────▼────────────────┐
    #  │ build_merged_chunk_text()│  │  일반 데이터는       │
    #  │  (일주일/전체 통합 빌드) │  │  그 자리에서 즉시 청크│
    #  └────────────────┬──────┘  └─────┬────────────────┘
    #                   │               │
    #                   └───────┬───────┘
    #                           │
    #            ┌──────────────▼──────────────┐
    #            │      최종 refined_chunks     │
    #            └─────────────────────────────┘