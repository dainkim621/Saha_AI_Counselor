from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, Date, Boolean
from pgvector.sqlalchemy import Vector  # 추가
from sqlalchemy.sql import func
from app.database import Base
    
class Notice(Base):
    __tablename__ = "notices"

    #고유 식별자 (청크 단위 관리를 위해 수정)
    # 기존 id 대신 JSONL에 있는 chunk_id를 PK로 쓰거나, 별도 PK를 둠.
    id = Column(Integer, primary_key=True, index=True) 
    chunk_id = Column(String, unique=True, index=True, nullable=False) # 예: doc_id_0
    doc_id = Column(String, index=True, nullable=False) # 원본 문서 ID
    
    # 2. 메타데이터 (검색 및 필터링용)
    url = Column(String, nullable=False)
    source = Column(String, default="saha.go.kr")
    title = Column(String, nullable=False)
    author = Column(String) 
    published_at = Column(String, nullable=True) # 혹은 DateTime
    views = Column(Integer, default=0)
    menu_path = Column(JSON)       # ['전자민원', '사하구에 바란다'] 형태 저장
    page_type = Column(String, nullable=True)     # 크롤러 타입 구분용
    
    major = Column(String, nullable=True) # 대분류 (예: 증명민원 통합발급)
    minor = Column(String, nullable=True) # 중분류 (예: 인감증명발급)
    context = Column(Text, nullable=True)
    
    # 3. 데이터 본체 (가장 중요!)
    chunk_text = Column(Text, nullable=False) # AI가 읽을 핵심 텍스트
    chunk_index = Column(Integer)             # 문서 내 몇 번째 조각인지
    # full_text = Column(Text, nullable=True)   # (선택) 필요한 경우 원문 전체 저장

    # 4. 시스템 날짜
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # 크롤링 자동화 기능 만들면 주석 해제
    # updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    text_hash = Column(String, nullable=True)
    # 5. 벡터 검색 위한 컬럼 (1536차원)
    embedding = Column(Vector(1536))

# user_chat_logs를 SQLAlchemy에서 쓰기위해 UserChatLog 모델을 하나 추가
class UserChatLog(Base):
    __tablename__ = "user_chat_logs"

    id = Column(Integer, primary_key=True, index=True)

    # 사용자가 실제로 입력한 원본 질문
    search_query = Column(Text, nullable=False)

    # RAG 검색에 실제로 사용한 질문
    refined_query = Column(Text, nullable=True)

    # FAQ 그룹화를 위한 표준화된 질문
    normalized_query = Column(Text, nullable=True)

    # RAG 검색 과정에서 생성한 질문 임베딩 재사용
    embedding = Column(Vector(1536), nullable=True)

    # 사용자의 질문 언어
    # 예: ko, en, ja, zh
    language = Column(
        String,
        nullable=True
    )

    # 챗봇이 정상적인 답변을 생성했는지 여부
    # True: 정상 답변
    # False: 답변 실패
    answer_success = Column(
        Boolean,
        nullable=True
    )

    # 질문 입력 시간
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

# 관리자 계정 정보를 저장하는 테이블
class Admin(Base):
    __tablename__ = "admins"

    # 관리자 계정을 구분하기 위한 고유 번호
    id = Column(Integer, primary_key=True, index=True)

    # 관리자 로그인 ID
    # 같은 ID를 가진 관리자가 중복 생성되지 않도록 unique=True 설정
    username = Column(
        String,
        unique=True,
        index=True,
        nullable=False
    )

    # 관리자 비밀번호의 bcrypt 해시값
    # 실제 비밀번호 원문은 DB에 저장하지 않음
    password_hash = Column(
        String,
        nullable=False
    )

    # 관리자 이름
    name = Column(
        String,
        nullable=False
    )

    # 관리자 계정 활성화 여부
    # False인 경우 계정은 존재하더라도 로그인할 수 없도록 사용
    is_active = Column(
        Boolean,
        default=True,
        nullable=False
    )

    # 관리자 계정이 생성된 날짜와 시간
    # 계정 생성 시 DB에서 현재 시간을 자동으로 저장
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # 연속 로그인 실패 횟수
    # 로그인에 성공하면 다시 0으로 초기화
    failed_login_attempts = Column(
        Integer,
        default=0,
        nullable=False
    )

    # 로그인 잠금이 해제되는 날짜와 시간
    # 잠겨 있지 않은 계정은 None(NULL)
    locked_until = Column(
        DateTime(timezone=True),
        nullable=True
    )

# 로그인한 관리자의 세션 정보를 저장하는 테이블
class AdminSession(Base):
    __tablename__ = "admin_sessions"

    # 세션을 구분하기 위한 고유 번호
    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    # 이 세션을 사용하고 있는 관리자의 ID
    # admins 테이블의 관리자 id와 연결하기 위해 사용
    admin_id = Column(
        Integer,
        nullable=False,
        index=True
    )

    # 세션 토큰의 해시값
    # 실제 세션 토큰 원문은 DB에 저장하지 않고
    # SHA-256으로 해시한 값만 저장할 예정
    session_token_hash = Column(
        String,
        unique=True,
        nullable=False,
        index=True
    )

    # 세션이 생성된 날짜와 시간
    # 세션 생성 시 DB에서 현재 시간을 자동으로 저장
    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # 세션이 만료되는 날짜와 시간
    # 이 시간이 지나면 해당 로그인 세션을 사용할 수 없도록 할 예정
    expires_at = Column(
        DateTime(timezone=True),
        nullable=False
    )

