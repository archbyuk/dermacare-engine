"""
    Global 설정 CRUD API
    
    이 모듈은 Global 설정의 조회, 수정 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from db.session import get_db
from db.models.global_config import Global
from .utils import cascade_update_all_tables

# 라우터 설정
global_router = APIRouter(
    prefix="/admin/global",
    tags=["Global Config"]
)

# ============================================================================
# Pydantic 모델
# ============================================================================

class GlobalUpdateRequest(BaseModel):
    doc_price_minute: float
    aesthetician_price_minute: float

class GlobalResponse(BaseModel):
    doc_price_minute: float
    aesthetician_price_minute: float

    class Config:
        from_attributes = True

# ============================================================================
# Global API
# ============================================================================

"""Global 설정 조회"""
@global_router.get("/")
async def get_global_settings(db: Session = Depends(get_db)):
    # 시나리오: 관리자가 현재 의사/관리사 시간당 요금 설정을 확인
    # 구현: Global 테이블에서 Doc_Price_Minute, Aesthetician_Price_Minute 조회
    # 응답: 현재 설정된 요금 정보 반환
    
    try:
        global_settings = db.query(Global).first()
        if not global_settings:
            raise HTTPException(status_code=404, detail="Global 설정을 찾을 수 없습니다.")
        
        return GlobalResponse(
            doc_price_minute=global_settings.Doc_Price_Minute,
            aesthetician_price_minute=global_settings.Aesthetician_Price_Minute
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Global 설정 조회 중 오류가 발생했습니다: {str(e)}")

"""Global 설정 수정 (전체 시스템 영향)"""
@global_router.put("/")
async def update_global_settings(
    global_data: GlobalUpdateRequest, 
    db: Session = Depends(get_db)
):
    # 시나리오: 관리자가 의사/미용사 시간당 요금을 변경하여 전체 시스템의 원가에 영향
    # 구현:
    # 1. Global 테이블 업데이트 (Doc_Price_Minute, Aesthetician_Price_Minute)
    # 2. 모든 Element Procedure_Cost 재계산 (벌크 업데이트)
    # 3. 모든 Bundle Element_Cost 재계산 (벌크 업데이트)
    # 4. 모든 Custom Element_Cost 재계산 (벌크 업데이트)
    # 5. 모든 Sequence Procedure_Cost 재계산 (벌크 업데이트)
    # 6. 모든 Product 마진 재계산 (벌크 업데이트)
    # 7. 트랜잭션 커밋
    # 영향: 전체 시스템의 모든 원가가 변경되므로 가장 큰 규모의 업데이트
    
    try:
        # Global 설정 업데이트
        global_settings = db.query(Global).first()
        if not global_settings:
            raise HTTPException(status_code=404, detail="Global 설정을 찾을 수 없습니다.")
        
        global_settings.Doc_Price_Minute = global_data.doc_price_minute
        global_settings.Aesthetician_Price_Minute = global_data.aesthetician_price_minute
        
        # 전체 시스템 연쇄 업데이트 실행
        update_results = cascade_update_all_tables(db, global_settings)
        
        db.commit()
        
        return {
            "status": "success",
            "message": "Global 설정이 성공적으로 업데이트되었습니다.",
            "data": GlobalResponse(
                doc_price_minute=global_settings.Doc_Price_Minute,
                aesthetician_price_minute=global_settings.Aesthetician_Price_Minute
            ),
            "update_results": {
                "elements_updated": update_results.get('elements', 0),
                "bundles_updated": update_results.get('bundles', 0),
                "customs_updated": update_results.get('customs', 0),
                "sequences_updated": update_results.get('sequences', 0),
                "products_updated": update_results.get('products', 0)
            }
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Global 설정 업데이트 중 오류가 발생했습니다: {str(e)}")