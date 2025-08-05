from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from models import get_db, Enum

app = FastAPI(
    title="DermaCare API",
    description="DermaCare 시술 관리 시스템 API",
    version="1.0.0"
)

@app.get("/")
def root():
    return {"message": "This is DermaCare API server"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "api server is running properly"}

@app.get("/db-test")
def test_database_connection(db: Session = Depends(get_db)):
    """데이터베이스 연결 테스트"""
    try:
        # Enum 테이블에서 첫 번째 레코드 조회
        enum_count = db.query(Enum).count()
        return {
            "status": "success",
            "message": "database connection successful",
            "enum_count": enum_count
        }
    except Exception as e:
        return {
            "status": "error", 
            "message": f"Database connection failed: {str(e)}"
        }