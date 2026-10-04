import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin, AdminInvite
from app.api.admin_auth import require_admin


router = APIRouter()

# 관리자 초대 코드 유효 시간
ADMIN_INVITE_HOURS = 24


# 실제 초대 코드를 SHA-256으로 해시
# DB에는 초대 코드 원문이 아닌 해시값만 저장
def hash_invite_code(invite_code: str):
    return hashlib.sha256(
        invite_code.encode("utf-8")
    ).hexdigest()

@router.post("/invites")
def create_admin_invite(
    current_admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # 신규 관리자에게 전달할 실제 초대 코드 생성
    invite_code = secrets.token_urlsafe(24)

    # 실제 초대 코드는 DB에 저장하지 않고 해시값만 저장
    invite_code_hash = hash_invite_code(invite_code)

    # 현재 시간
    now = datetime.now(timezone.utc)

    # 초대 코드 만료 시간 설정
    expires_at = now + timedelta(hours=ADMIN_INVITE_HOURS)

    # DB에 저장할 초대 정보 생성
    admin_invite = AdminInvite(
        invite_code_hash=invite_code_hash,
        created_by=current_admin.id,
        expires_at=expires_at,
        is_used=False
    )

    db.add(admin_invite)
    db.commit()
    db.refresh(admin_invite)

    return {
        "message": "관리자 초대 코드가 생성되었습니다.",
        "invite_code": invite_code,
        "expires_at": expires_at
    }