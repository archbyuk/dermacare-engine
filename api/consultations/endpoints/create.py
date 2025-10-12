"""
    상담 관련 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db.session import get_db
from consultations.schema import (ConsultationCreateRequest, ConsultationCreateResponse)
from consultations.services.create_service import create_consultation

# 라우터 생성
create_router = APIRouter()

# 상담 내용 저장 API
@create_router.post("/create", response_model=ConsultationCreateResponse)
async def save_consultation(
    consultation_data: ConsultationCreateRequest,
    db: Session = Depends(get_db)
):
    
    try:
        result = create_consultation(db, consultation_data)
        return result
        
    except HTTPException:
        raise
    
    except Exception as e:
        
        raise HTTPException(
            status_code=500,
            detail=f"상담 저장 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )
