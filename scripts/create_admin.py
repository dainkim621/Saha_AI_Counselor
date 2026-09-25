import bcrypt
from getpass import getpass

from app.database import SessionLocal
from app.models import Admin


def create_admin():
    username = input("관리자 ID: ").strip()
    name = input("관리자 이름: ").strip()
    password = getpass("관리자 비밀번호: ")
    
    # 빈 값 검사 + 관리자 ID 중복 검사
    if not username or not name or not password:
        print("ID, 이름, 비밀번호는 모두 입력해야 합니다.")
        return

    db = SessionLocal() # 기존 프로젝트 DB에 접속할 SQLAlchemy 세션 만듬

    try:
        existing_admin = (
            db.query(Admin)
            .filter(Admin.username == username)
            .first() # 입력한 관리자 ID와 같은 계정이 이미 있는지 찾음
        )

        if existing_admin:
            print("이미 존재하는 관리자 ID입니다.")
            return

        # 비밀번호 해시: 사용자가 입력한 비밀번호 bcrypy 해시로 변환
        password_hash = bcrypt.hashpw( 
            password.encode("utf-8"),
            bcrypt.gensalt()
        ).decode("utf-8")
        
        # 관리자 객체 생성
        new_admin = Admin(
            username=username,
            name=name,
            password_hash=password_hash,
            is_active=True
        )
        
        # DB 저장
        db.add(new_admin)
        db.commit()

        print("관리자 계정이 생성되었습니다.")

    except Exception as e:
        db.rollback()
        print(f"관리자 계정 생성 중 오류가 발생했습니다: {e}")

    finally:
        db.close()

if __name__ == "__main__":
    create_admin()