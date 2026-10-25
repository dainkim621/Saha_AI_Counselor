import hashlib
import secrets

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Admin, AdminInvite, AdminSession
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


# 관리자 계정 목록 조회
@router.get("/admins")
def get_admin_list(
    current_admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # DB에 등록된 관리자 전체 조회
    admins = (
        db.query(Admin)
        .order_by(Admin.created_at.desc(), Admin.id.desc())
        .all()
    )

    # 화면에 필요한 정보만 반환
    return {
        "admins": [
            {
                "id": admin.id,
                "username": admin.username,
                "name": admin.name,
                "is_active": admin.is_active,
                "is_super_admin": admin.is_super_admin,
                "created_at": admin.created_at,
                "is_current": admin.id == current_admin.id,
            }
            for admin in admins
        ]
    }

    
# =========================================
# 관리자 계정 활성화 / 비활성화
# =========================================

# 관리자 상태 변경 요청 데이터
class AdminStatusUpdate(BaseModel):
    is_active: bool


@router.patch("/admins/{admin_id}/status")
def update_admin_status(
    admin_id: int,
    payload: AdminStatusUpdate,
    current_admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # 1. 최고 관리자 권한 확인
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="최고 관리자만 계정 상태를 변경할 수 있습니다."
        )

    # 2. 본인 계정 변경 방지
    if current_admin.id == admin_id:
        raise HTTPException(
            status_code=403,
            detail="본인 계정의 상태는 변경할 수 없습니다."
        )

    # 3. 변경할 관리자 계정 조회
    target_admin = (
        db.query(Admin)
        .filter(Admin.id == admin_id)
        .with_for_update()
        .first()
    )

    if target_admin is None:
        raise HTTPException(
            status_code=404,
            detail="관리자 계정을 찾을 수 없습니다."
        )

    # 4. 다른 최고 관리자 계정 보호
    if target_admin.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="최고 관리자 계정의 상태는 변경할 수 없습니다."
        )

    # 5. 계정 활성화 상태 변경
    target_admin.is_active = payload.is_active

    # 6. 비활성화 시 기존 관리자 세션 삭제
    if not payload.is_active:
        db.query(AdminSession).filter(
            AdminSession.admin_id == target_admin.id
        ).delete(synchronize_session=False)

    # 7. DB 변경사항 저장
    db.commit()
    db.refresh(target_admin)

    return {
        "message": (
            "관리자 계정이 활성화되었습니다."
            if target_admin.is_active
            else "관리자 계정이 비활성화되었습니다."
        ),
        "admin": {
            "id": target_admin.id,
            "username": target_admin.username,
            "name": target_admin.name,
            "is_active": target_admin.is_active
        }
    }

# =========================================
# 관리자 초대 코드 발급 이력 조회
# =========================================

@router.get("/invites/history")
def get_admin_invite_history(
    current_admin: Admin = Depends(require_admin),
    db: Session = Depends(get_db)
):
    # 최고 관리자만 전체 초대 코드 이력 조회 가능
    if not current_admin.is_super_admin:
        raise HTTPException(
            status_code=403,
            detail="최고 관리자만 초대 코드 이력을 조회할 수 있습니다."
        )

    # 현재 시간 (UTC)
    now = datetime.now(timezone.utc)

    # 초대 코드 목록 조회 (최근 만료일 순)
    invites = (
        db.query(AdminInvite)
        .order_by(AdminInvite.expires_at.desc())
        .all()
    )

    invite_history = []

    for invite in invites:
        expires_at = invite.expires_at

        # DB에 UTC 기준 시간대 정보가 없는 경우 처리
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(
                tzinfo=timezone.utc
            )

        # 초대 코드 상태 확인
        if invite.is_used:
            status = "used"
        elif expires_at <= now:
            status = "expired"
        else:
            status = "available"

        invite_history.append({
            "id": invite.id,
            "created_by": invite.created_by,
            "created_at": getattr(
                invite, "created_at", None
            ),
            "expires_at": expires_at,
            "is_used": invite.is_used,
            "status": status
        })

    # 현재 사용 가능한 초대 코드 수
    available_count = sum(
        1 for invite in invite_history
        if invite["status"] == "available"
    )

    return {
        "total_invites": len(invite_history),
        "available_count": available_count,
        "invites": invite_history
    }





