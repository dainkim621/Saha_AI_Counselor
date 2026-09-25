import bcrypt
import secrets
import hashlib

from fastapi import APIRouter, Depends, HTTPException, Response, Cookie
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models import Admin, AdminSession

router = APIRouter()

# 관리자 로그인 세션 유지 시간
ADMIN_SESSION_HOURS = 8

# 관리자 로그인 연속 실패 허용 횟수
MAX_LOGIN_ATTEMPTS = 5

# 로그인 잠금 시간(분)
LOGIN_LOCK_MINUTES = 15

class AdminLoginRequest(BaseModel):
    username: str
    password: str

# 예측하기 어려운 안전한 관리자 세션 토큰 생성
def create_session_token():
    return secrets.token_urlsafe(32)


# 실제 세션 토큰을 SHA-256으로 해시
# DB에는 세션 토큰 원문 대신 이 해시값만 저장
def hash_session_token(token: str):
    return hashlib.sha256(
        token.encode("utf-8")
    ).hexdigest()

# 관리자 인증이 필요한 API에서 공통으로 사용할 함수
def require_admin(
    # 브라우저의 관리자 세션 쿠키를 가져옴
    admin_session: str | None = Cookie(default=None),

    # DB 세션 받아오기
    db: Session = Depends(get_db)
):
    # 세션 쿠키가 없으면 로그인하지 않은 상태
    if not admin_session:
        raise HTTPException(
            status_code=401,
            detail="로그인이 필요합니다."
        )

    # 브라우저가 가지고 있는 실제 세션 토큰을
    # SHA-256으로 해시하여 DB에 저장된 값과 비교
    session_token_hash = hash_session_token(admin_session)

    # DB에서 해당 세션 조회
    session = (
        db.query(AdminSession)
        .filter(
            AdminSession.session_token_hash == session_token_hash
        )
        .first()
    )

    # 일치하는 세션이 없으면 인증 실패
    if not session:
        raise HTTPException(
            status_code=401,
            detail="유효하지 않은 로그인 세션입니다."
        )

    # 현재 시간을 UTC 기준으로 가져옴
    now = datetime.now(timezone.utc)

    # 세션이 만료되었는지 확인
    if session.expires_at <= now:
        # 만료된 세션은 DB에서도 삭제
        db.delete(session)
        db.commit()

        raise HTTPException(
            status_code=401,
            detail="로그인 세션이 만료되었습니다."
        )

    # 세션에 연결된 관리자 계정 조회
    admin = (
        db.query(Admin)
        .filter(Admin.id == session.admin_id)
        .first()
    )

    # 관리자 계정이 없거나 비활성화된 경우 접근 차단
    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=403,
            detail="사용할 수 없는 관리자 계정입니다."
        )

    # 인증에 성공한 관리자 객체 반환
    return admin

@router.post("/login")
def admin_login(
    request: AdminLoginRequest,
    response: Response,
    db: Session = Depends(get_db) # 기존 프로젝트의 get_db()를 이용해 DB 세션 받아오기
):
    admin = ( # admins 테이블에서 입력한 ID 찾기
        db.query(Admin)
        .filter(Admin.username == request.username)
        .first()
    )

    if not admin:  # 입력한 ID와 일치하는 관리자 계정이 없을 때
        raise HTTPException(
            status_code=401,
            detail="아이디 또는 비밀번호가 올바르지 않습니다."
        )

    if not admin.is_active: # 비활성화된 관리자 계정의 로그인 막음
        raise HTTPException(
            status_code=403,
            detail="비활성화된 관리자 계정입니다."
        )

    # 현재 시간을 UTC 기준으로 가져옴
    now = datetime.now(timezone.utc)

    # 계정에 로그인 잠금 시간이 설정되어 있는 경우
    if admin.locked_until:
        # 아직 잠금 시간이 지나지 않았다면 로그인 차단
        if admin.locked_until > now:
            raise HTTPException(
                status_code=429,
                detail="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해주세요."
            )

        # 잠금 시간이 이미 지났다면 잠금 상태와 실패 횟수 초기화
        admin.locked_until = None
        admin.failed_login_attempts = 0
        db.commit()

    password_matches = bcrypt.checkpw(
        request.password.encode("utf-8"),
        admin.password_hash.encode("utf-8")
    )

    if not password_matches:
        # 비밀번호가 틀리면 로그인 실패 횟수를 1 증가
        admin.failed_login_attempts += 1

        # 연속 로그인 실패가 5회 이상이면
        # 현재 시점부터 15분 동안 해당 관리자 계정을 잠금
        if admin.failed_login_attempts >= MAX_LOGIN_ATTEMPTS:
            admin.locked_until = now + timedelta(
                minutes=LOGIN_LOCK_MINUTES
            )

        # 변경된 실패 횟수와 잠금 시간을 DB에 저장
        db.commit()

        # 보안을 위해 아이디가 맞고 비밀번호만 틀렸다는 사실을
        # 구체적으로 알려주지 않고 동일한 오류 메시지를 반환
        raise HTTPException(
            status_code=401,
            detail="아이디 또는 비밀번호가 올바르지 않습니다."
        )
    
    # 로그인에 성공하면 이전 로그인 실패 횟수를 초기화
    admin.failed_login_attempts = 0
    admin.locked_until = None
    
    # 초기화된 값을 DB에 저장
    db.commit()

    # 같은 관리자 계정으로 만들어진 기존 로그인 세션을 모두 삭제
    # 한 관리자 계정당 하나의 로그인 세션만 유지
    db.query(AdminSession).filter(
        AdminSession.admin_id == admin.id
    ).delete(synchronize_session=False)
    
    db.commit()
    
    # 로그인에 성공했으므로 새로운 세션 토큰 생성
    session_token = create_session_token()
    
    # 실제 세션 토큰은 DB에 저장하지 않고
    # SHA-256으로 해시한 값만 저장
    session_token_hash = hash_session_token(session_token)
    
    # 현재 시간을 UTC 기준으로 가져옴
    now = datetime.now(timezone.utc)
    
    # 관리자 세션의 만료 시간 설정
    # 우선 8시간 후 자동 만료되도록 설정
    expires_at = now + timedelta(hours=ADMIN_SESSION_HOURS)
    
    # DB에 저장할 관리자 세션 생성
    admin_session = AdminSession(
        admin_id=admin.id,
        session_token_hash=session_token_hash,
        expires_at=expires_at
    )
    
    # 생성한 세션을 DB에 저장
    db.add(admin_session)
    db.commit()

    # 생성한 실제 세션 토큰을 브라우저의 HttpOnly 쿠키에 저장
    response.set_cookie(
        key="admin_session",
        value=session_token,
        
        # JavaScript에서 쿠키 값을 읽지 못하도록 설정
        httponly=True,
        
        # 다른 사이트에서 발생한 요청에는 쿠키 전송을 제한
        samesite="strict",
        
        # 개발 환경은 HTTP이므로 우선 False
        # 실제 HTTPS 배포 환경에서는 반드시 True로 변경
        secure=False,
        
        # 쿠키를 8시간 후 만료
        max_age=ADMIN_SESSION_HOURS * 60 * 60,
        
        # 전체 관리자 API 요청에서 사용할 수 있도록 설정
        path="/"
    )

    return {
        "message": "로그인에 성공했습니다.",
        "admin": {
            "id": admin.id,
            "username": admin.username,
            "name": admin.name
        }
    }

# 현재 로그인한 관리자 정보를 확인하는 API
@router.get("/me")
def get_current_admin(
    # require_admin()에서 세션의 유효성을 검사하고
    # 인증에 성공한 관리자 객체를 받아옴
    current_admin: Admin = Depends(require_admin)
):
    return {
        "id": current_admin.id,
        "username": current_admin.username,
        "name": current_admin.name
    }

# 현재 로그인한 관리자 로그아웃 API
@router.post("/logout")
def admin_logout(
    response: Response,

    # 브라우저에 저장된 관리자 세션 쿠키를 가져옴
    admin_session: str | None = Cookie(default=None),

    db: Session = Depends(get_db)
):
    # 세션 쿠키가 존재하는 경우
    if admin_session:
        # 실제 세션 토큰을 SHA-256으로 해시
        session_token_hash = hash_session_token(admin_session)

        # DB에서 해당 세션 조회
        session = (
            db.query(AdminSession)
            .filter(
                AdminSession.session_token_hash == session_token_hash
            )
            .first()
        )

        # DB에 세션이 존재하면 삭제
        if session:
            db.delete(session)
            db.commit()

    # 브라우저에 저장된 HttpOnly 세션 쿠키 삭제
    response.delete_cookie(
        key="admin_session",
        path="/"
    )

    return {
        "message": "로그아웃되었습니다."
    }