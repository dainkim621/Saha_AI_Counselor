from zoneinfo import ZoneInfo
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import extract
from app.database import get_db
from app.models import Admin, UserChatLog
from app.api.admin_auth import require_admin
from datetime import datetime, timedelta
from sqlalchemy import func

from datetime import timezone  # 시간
from zoneinfo import ZoneInfo

# 관리자 대시보드 전용 라우터
router = APIRouter()


# 관리자 대시보드 상단 요약 통계 API
@router.get("/summary")
def get_dashboard_summary(
    current_admin: Admin = Depends(require_admin), # 유효한 관리자 세션이 있는 경우에만 접근 가능
    db: Session = Depends(get_db) # 통계 조회에 사용할 DB 세션
):
    # 최근 7일 날짜 계산 (필요시 날짜 범위 적용)
    one_week_ago = datetime.utcnow() - timedelta(days=7)
    
    # 1. 최근 7일 전체 질문 수 (날짜 조건 빼고 전체를 보려면 .filter() 부분을 지우셔도 됩니다)
    total_questions = (
        db.query(func.count(UserChatLog.id))
        .filter(UserChatLog.created_at >= one_week_ago)
        .scalar()
    ) or 0
    
    # 2. 답변 실패 질문 수
    failed_count = (
        db.query(func.count(UserChatLog.answer_success))
        .filter(UserChatLog.created_at >= one_week_ago)
        .filter(UserChatLog.answer_success == False)
        .scalar()
    ) or 0

    print(f"👉 [DEBUG] 조회된 총 질문 수: {total_questions}, 실패 수: {failed_count}")

    # 프론트엔드가 요구하는 형식에 맞춰 데이터 반환
    return {
        "totalQuestions": total_questions,
        "failedQuestionCount": failed_count,
        "topLanguage": "한국어",
        "peakHour": "14:00 - 15:00",
        "admin": current_admin.username
    }
    
@router.get("/failed-questions")
def get_failed_questions(
    current_admin: Admin = Depends(require_admin), # 관리자만 볼 수 있도록 보호
    db: Session = Depends(get_db)
):
    # 실패한 로그 중 필요한 3가지 컬럼(+ id, 시간)만 추출하여 최신순으로 가져옴
    failed_logs = (
        db.query(
            UserChatLog.id,
            UserChatLog.search_query,
            UserChatLog.failure_category,
            UserChatLog.failure_reason,
            UserChatLog.created_at
        )
        .filter(UserChatLog.answer_success == False)
        .order_by(UserChatLog.id.desc())
        .limit(10) # 대시보드 성능을 위해 최근 100개만 전송
        .all()
    )

    # 프론트엔드의 FailedQuestion 타입에 맞춰 JSON 형태로 변환
    return [
        {
            "id": log.id,
            "question": log.search_query,
            "category": log.failure_category or "NONE",
            "reason": log.failure_reason or "",
            "createdAt": log.created_at.strftime("%Y-%m-%d %H:%M") if log.created_at else ""
        }
        for log in failed_logs
    ]
    

# 시간대별 이용량 조회 API
@router.get("/hourly-usage")
def get_hourly_usage(
    current_admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # 최근 7일간의 질문을 한국시간 기준으로 집계
    now_kst = datetime.now(ZoneInfo("Asia/Seoul"))
    one_week_ago = now_kst - timedelta(days=7)

    # created_at을 한국시간으로 변환한 뒤 시간 추출
    hour_expression = func.extract(
        "hour",
        func.timezone("Asia/Seoul", UserChatLog.created_at)
    )

    results = (
        db.query(
            hour_expression.label("hour"),
            func.count(UserChatLog.id).label("count")
        )
        .filter(UserChatLog.created_at >= one_week_ago)
        .group_by(hour_expression)
        .order_by(hour_expression)
        .all()
    )

    # 질문이 없는 시간도 0건으로 표시
    count_by_hour = {
        int(row.hour): row.count
        for row in results
    }

    hourly_stats = [
        {
            "hour": f"{hour:02d}:00",
            "count": count_by_hour.get(hour, 0)
        }
        for hour in range(24)
    ]

    # 가장 질문이 많은 시간대
    peak_hour = max(
        hourly_stats,
        key=lambda item: item["count"]
    )

    if peak_hour["count"] == 0:
        peak_hour_text = "데이터 없음"
    else:
        start_hour = int(peak_hour["hour"][:2])
        end_hour = (start_hour + 1) % 24

        peak_hour_text = (
            f"{start_hour:02d}:00 - {end_hour:02d}:00"
        )

    return {
        "peakHour": peak_hour_text,
        "hourlyUsage": hourly_stats
    }
