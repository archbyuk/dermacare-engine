from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# 환경변수 로드
load_dotenv()

# 데이터베이스 URL 설정
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    DATABASE_URL,
    echo=True,  # SQL 쿼리 로깅
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=3600,  # 연결 재사용 시간 (1시간)
)

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 데이터베이스 세션 의존성
def get_db():
    """ 데이터베이스 세션을 생성하고 반환하는 의존성 함수 """
    db = SessionLocal() # 새로운 세션 생성
    
    try:
        yield db  # 세션을 API EndPoint에 전달
    
    finally:
        db.close() # 요청 완료 후 세션 정리
        
