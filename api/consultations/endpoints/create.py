"""
    상담 관련 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from db.session import get_db
from consultations.schema import (ConsultationCreateRequest, ConsultationCreateResponse)
from consultations.services.create_service import create_consultation
from security.permissions import require_permission

# 라우터 생성
create_router = APIRouter()

# 상담 내용 저장 API
@create_router.post("/create", response_model=ConsultationCreateResponse)
@require_permission("consultation:create:own")
def save_consultation(
    request: Request,
    consultation_data: ConsultationCreateRequest,
    db: Session = Depends(get_db)
):
    
    try:
        # 사용자 정보 추출 (상담 생성자 식별용)
        user_info = request.state.user
        user_uuid = user_info.get("user_uuid")
        
        # 상담 생성 시 사용자 정보 전달
        result = create_consultation(db, consultation_data, user_uuid)
        return result
        
    except HTTPException:
        raise
    
    except Exception as e:
        
        raise HTTPException(
            status_code=500,
            detail=f"상담 저장 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )
