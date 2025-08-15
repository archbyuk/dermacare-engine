"""
    헬스체크 및 시스템 상태 확인 API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.session import get_db
from db.models.enum import Enum

health_router = APIRouter(
    prefix="/health",
    tags=["Health Check"]
)

@health_router.get("/")
def health_check():
    """기본 헬스체크"""
    return {
        "status": "healthy", 
        "message": "DermaCare API server is running properly"
    }

@health_router.get("/db")
def test_database_connection(db: Session = Depends(get_db)):
    """데이터베이스 연결 테스트"""
    try:
        # Enum 테이블에서 레코드 수 조회
        enum_count = db.query(Enum).count()
        return {
            "status": "success",
            "message": "Database connection successful",
            "enum_count": enum_count
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Database connection failed: {str(e)}"
        }