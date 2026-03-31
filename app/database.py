from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# 1. DB 접속 주소 설정 (도커 설정과 일치해야 함)
# postgresql://[사용자]:[비밀번호]@[호스트]:[포트]/[DB이름]
SQLALCHEMY_DATABASE_URL = "postgresql://postgres:saha1234@localhost:5432/saha_db"

# 2. 커넥션 엔진 생성
engine = create_engine(SQLALCHEMY_DATABASE_URL)

# 3. DB와 대화하기 위한 세션 클래스
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. 나중에 models.py에서 상속받을 기본 클래스
Base = declarative_base()

# 5. DB 연결을 관리하는 함수 (Dependency Injection용)
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()