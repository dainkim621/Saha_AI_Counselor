import os
from datetime import datetime



# ---------------------------------------------------------------------------
# [4] 검수용 HTML 생성 전용 함수
# ---------------------------------------------------------------------------
def generate_html_dashboard(chunks, output_path):
    """수집된 청크 리스트를 바탕으로 인간 검수용 대시보드 HTML을 렌더링하는 함수"""
    html_content = f"""<!DOCTYPE html>
    <html lang="ko">
    <head>
        <meta charset="UTF-8">
        <title>사하구청 챗봇 RAG 데이터 검수 대시보드</title>
        <style>
            body {{ font-family: 'Segoe UI', sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }}
            .container {{ max-width: 1200px; margin: 0 auto; }}
            header {{ background: linear-gradient(135deg, #2c3e50, #2980b9); color: white; padding: 25px; border-radius: 12px; margin-bottom: 25px; }}
            header h1 {{ margin: 0; font-size: 28px; }}
            .stats {{ display: inline-block; background: rgba(255,255,255,0.2); padding: 5px 15px; border-radius: 20px; margin-top: 10px; font-weight: bold; }}
            .card {{ background: white; border-radius: 10px; padding: 20px; margin-bottom: 20px; border-left: 6px solid #2980b9; }}
            .card.civil {{ border-left-color: #27ae60; }}
            .card.bid {{ border-left-color: #e67e22; }}
            .card.waste {{ border-left-color: #8e44ad; }}
            .meta-row {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; border-bottom: 1px dashed #eee; padding-bottom: 8px; }}
            .doc-id {{ font-family: monospace; font-weight: bold; color: #7f8c8d; background: #eaedf1; padding: 3px 8px; border-radius: 4px; }}
            .badge {{ padding: 4px 10px; border-radius: 20px; color: white; font-size: 12px; font-weight: bold; background-color: #2980b9; }}
            .badge.civil {{ background-color: #27ae60; }}
            .badge.bid {{ background-color: #e67e22; }}
            .badge.waste {{ background-color: #8e44ad; }}
            .title {{ font-size: 18px; font-weight: bold; color: #2c3e50; }}
            .content-box {{ background-color: #fafbfc; border: 1px solid #e1e4e8; border-radius: 6px; padding: 15px; white-space: pre-wrap; line-height: 1.6; margin-top: 10px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <header>
                <h1>사하구청 AI 상담사 고우니 - RAG 청크 검수 대시보드 🐳</h1>
                <div class="stats">📋 정제 완료된 총 청크 수: {len(chunks)}개</div>
            </header>
            <div class="list">
    """
    for chunk in chunks:
        ptype = chunk.get("page_type", "")
        card_cls, badge_cls = "card", "badge"
        
        # [1] 새로 통합한 page_type 키워드 조건에 맞게 CSS 테마 매칭
        if "civil" in ptype or "민원" in ptype: 
            card_cls, badge_cls = "card civil", "badge civil"
        elif "bid" in ptype or "입찰" in ptype: 
            card_cls, badge_cls = "card bid", "badge bid"
        elif "waste" in ptype or "폐기물" in ptype: 
            card_cls, badge_cls = "card waste", "badge waste"
            
        # [2] chunk.get('text') 대신 스키마와 통일한 chunk_text를 안전하게 가져옴
        text_content = chunk.get("chunk_text", "") or ""
        safe_text = text_content.replace('<', '&lt;').replace('>', '&gt;')
            
        html_content += f"""
                <div class="{card_cls}">
                    <div class="meta-row">
                        <span class="doc-id">ID: {chunk.get('chunk_id')}</span>
                        <span class="{badge_cls}">{ptype}</span>
                    </div>
                    <div class="title">{chunk.get('title')}</div>
                    <a href="{chunk.get('url')}" target="_blank" style="font-size:13px; color:#3498db; text-decoration:none;">🔗 원본 구청 페이지</a>
                    <div class="content-box">{safe_text}</div>
                </div>
        """
    html_content += "</div></div></body></html>"
    
    # 디렉토리가 없으면 생성 후 저장
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html_content)
