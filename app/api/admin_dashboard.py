from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin
from app.api.admin_auth import require_admin


# 관리자 대시보드 전용 라우터
router = APIRouter()


# 관리자 대시보드 상단 요약 통계 API
@router.get("/summary")
def get_dashboard_summary(
    # 유효한 관리자 세션이 있는 경우에만 접근 가능
    current_admin: Admin = Depends(require_admin),

    # 통계 조회에 사용할 DB 세션
    db: Session = Depends(get_db)
):
    # 우선 관리자 인증이 정상적으로 적용되는지 확인하기 위한 임시 응답
    return {
        "message": "관리자 인증 성공",
        "admin": current_admin.username
    }