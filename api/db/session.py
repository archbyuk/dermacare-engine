from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
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

# ============================== #

# 데이터베이스 URL 설정(sync)
SYNC_DATABASE_URL = (
    f"mysql+mysqlconnector://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# SQLAlchemy 엔진 생성
engine = create_engine(
    SYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=3600,   # 연결 재사용 시간 (1시간)
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

# ============================== #

# 데이터베이스 URL 설정(async)
ASYNC_DATABASE_URL = (
    f"mysql+aiomysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

# SQLAlchemy 엔진 생성
async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=3600,  # 연결 재사용 시간 (1시간)
)
        
# 비동기 세션 팩토리
AsyncSessionLocal = async_sessionmaker(
    async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 커밋 후에도 객체 사용 가능
    autocommit=False,
    autoflush=False
)

async def get_async_db():
    """ 비동기 데이터베이스 세션 """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        
        finally:
            await session.close()