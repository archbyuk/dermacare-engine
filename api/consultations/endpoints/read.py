"""
    상담 조회 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from db.session import get_db
from consultations.schema import (
    ConsultationReadRequest,
    ConsultationListResponse
)
from consultations.services.read_service import get_consultations

# 라우터 생성
read_router = APIRouter()

# 상담 목록 조회 API
@read_router.get("/read", response_model=ConsultationListResponse)
async def read_consultations(
    cursor: int = Query(None, description="커서 ID (이전 조회의 마지막 ID)"),
    limit: int = Query(30, ge=1, le=100, description="조회할 개수 (기본 30개, 최대 100개)"),
    sort_by: str = Query("id", description="정렬 기준 (id, consultation_date, customer_name, created_at)"),
    sort_order: str = Query("desc", description="정렬 순서 (asc: 오름차순, desc: 내림차순)"),
    db: Session = Depends(get_db)
):

    try:
        request = ConsultationReadRequest(cursor=cursor, limit=limit, sort_by=sort_by, sort_order=sort_order)
        result = get_consultations(db, request)
        
        return result
        
    except HTTPException:
        raise
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상담 조회 중 예상치 못한 오류가 발생했습니다: {str(e)}"
        )
