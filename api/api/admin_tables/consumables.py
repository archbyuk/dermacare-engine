"""
    Consumables CRUD API
    
    이 모듈은 Consumables의 생성, 조회, 수정, 삭제, 비활성화/활성화 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel

from db.session import get_db
from db.models.consumables import Consumables
from db.models.global_config import Global
from .utils import cascade_update_by_consumable, calculate_unit_price, calculate_vat

# 라우터 설정
consumables_router = APIRouter(
    prefix="/consumables",
    tags=["Consumables"]
)

# ============================================================================
# Pydantic 모델
# ============================================================================

class ConsumableCreateRequest(BaseModel):
    id: int
    name: str
    unit_price: float
    unit_type: str
    description: Optional[str] = None
    price: Optional[int] = None
    i_value: Optional[int] = None
    f_value: Optional[float] = None
    taxable_type: Optional[str] = "과세"
    covered_type: Optional[str] = "비급여"

class ConsumableUpdateRequest(BaseModel):
    # Element Cost에 영향 없음
    name: Optional[str] = None
    description: Optional[str] = None
    release: Optional[int] = None
    
    # Unit_Price 재계산 필요
    unit_type: Optional[str] = None
    
    # Element Cost에 직접 영향 (연쇄 업데이트 필요)
    unit_price: Optional[float] = None
    price: Optional[float] = None
    i_value: Optional[int] = None
    f_value: Optional[float] = None
    
    # VAT 계산에 영향
    taxable_type: Optional[str] = None
    
    # 급여분류 (Element Cost에 영향 없음)
    covered_type: Optional[str] = None

class ConsumableResponse(BaseModel):
    id: int
    name: str
    unit_price: float
    unit_type: str
    description: Optional[str] = None
    release: int
    price: int
    i_value: Optional[int] = None
    f_value: Optional[float] = None
    vat: int
    taxable_type: str
    covered_type: str

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.ID,
            name=obj.Name,
            unit_price=obj.Unit_Price,
            unit_type=obj.Unit_Type,
            description=obj.Description,
            release=obj.Release,
            price=obj.Price,
            i_value=obj.I_Value,
            f_value=obj.F_Value,
            vat=obj.VAT,
            taxable_type=obj.TaxableType,
            covered_type=obj.Covered_Type
        )

# ============================================================================
# Consumables API
# ============================================================================

@consumables_router.get("/")
async def get_consumables_list(
    search: Optional[str] = Query(None, description="검색어"),
    db: Session = Depends(get_db)
):
    """Consumables 목록 조회 (검색어가 있으면 필터링, 없으면 전체 조회)"""
    # 시나리오: 관리자가 소모품을 조회하거나 검색할 수 있도록 함
    # 구현: 검색어가 없으면 모든 소모품 조회, 검색어가 있으면 이름으로 필터링
    # 응답: Consumables 목록 반환
    
    try:
        if not search:
            # 검색어가 없으면 모든 소모품 조회
            consumables = db.query(Consumables).all()
        else:
            # 검색어가 있으면 이름으로 필터링
            consumables = db.query(Consumables).filter(
                Consumables.Name.contains(search)
            ).all()
        
        return [ConsumableResponse.from_orm(consumable) for consumable in consumables]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consumables 조회 중 오류가 발생했습니다: {str(e)}")

@consumables_router.get("/{consumable_id}")
async def get_consumable_detail(consumable_id: int, db: Session = Depends(get_db)):
    """Consumable 상세 조회"""
    # 시나리오: 특정 Consumable의 상세 정보를 확인
    # 구현: Consumables 테이블에서 특정 Consumable의 모든 정보 조회 (Release 상태와 관계없이)
    # 응답: Consumable의 상세 정보 반환
    
    try:
        consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_id
        ).first()
        
        if not consumable:
            raise HTTPException(status_code=404, detail="Consumable을 찾을 수 없습니다.")
        
        return ConsumableResponse.from_orm(consumable)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Consumable 상세 조회 중 오류가 발생했습니다: {str(e)}")

@consumables_router.post("/")
async def create_consumable(
    consumable_data: ConsumableCreateRequest, 
    db: Session = Depends(get_db)
):
    """Consumables 생성"""
    # 시나리오: 새로운 소모품을 시스템에 추가
    # 구현:
    # 1. ID 중복 체크
    # 2. Consumables 테이블에 새 소모품 추가 (Name, Unit_Price, Unit_Type, Description)
    # 3. Release=1로 설정하여 활성화
    # 4. 트랜잭션 커밋
    # 영향: 새로 생성된 소모품은 아직 사용되지 않으므로 다른 테이블에 영향 없음
    
    try:
        # ID 중복 체크
        existing_consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_data.id
        ).first()
        
        if existing_consumable:
            raise HTTPException(
                status_code=400, 
                detail=f"ID {consumable_data.id}는 이미 사용 중입니다. 다른 ID를 사용해주세요."
            )
        
        # 기본값 설정
        price = consumable_data.price or consumable_data.unit_price
        i_value = consumable_data.i_value
        f_value = consumable_data.f_value or 1.0
        taxable_type = consumable_data.taxable_type or "과세"
        covered_type = consumable_data.covered_type or "비급여"
        
        # Unit_Price와 VAT 계산
        if consumable_data.price and (consumable_data.i_value or consumable_data.f_value):
            unit_price = calculate_unit_price(price, i_value or -1, f_value)
        else:
            unit_price = consumable_data.unit_price
        
        vat = calculate_vat(unit_price, taxable_type)
        
        new_consumable = Consumables(
            ID=consumable_data.id,
            Name=consumable_data.name,
            Unit_Price=unit_price,
            Unit_Type=consumable_data.unit_type,
            Description=consumable_data.description,
            Price=price,
            I_Value=i_value,
            F_Value=f_value,
            VAT=vat,
            TaxableType=taxable_type,
            Covered_Type=covered_type,
            Release=1
        )
        
        db.add(new_consumable)
        db.commit()
        db.refresh(new_consumable)
        
        return {
            "status": "success",
            "message": "소모품이 성공적으로 생성되었습니다.",
            "data": ConsumableResponse.from_orm(new_consumable)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"소모품 생성 중 오류가 발생했습니다: {str(e)}")

@consumables_router.put("/{consumable_id}")
async def update_consumable(
    consumable_id: int, 
    consumable_data: ConsumableUpdateRequest, 
    db: Session = Depends(get_db)
):
    """Consumables 수정 (관련 Element 영향)"""
    # 시나리오: 소모품의 단가나 정보를 변경하여 해당 소모품을 사용하는 Element들의 원가에 영향
    # 구현:
    # 1. Consumables 테이블 업데이트 (Name, Unit_Price, Unit_Type, Description, I_Value, F_Value, Price)
    # 2. 해당 소모품을 사용하는 모든 Element들의 Procedure_Cost 재계산
    # 3. 관련 Bundle Element_Cost 재계산 (벌크 업데이트)
    # 4. 관련 Custom Element_Cost 재계산 (벌크 업데이트)
    # 5. 관련 Sequence Procedure_Cost 재계산 (벌크 업데이트)
    # 6. 관련 Product 마진 재계산 (벌크 업데이트)
    # 7. 트랜잭션 커밋
    # 영향: 해당 소모품을 사용하는 Element들과 그 상위 테이블들에만 영향
    
    try:
        consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_id,
            Consumables.Release == 1
        ).first()
        
        if not consumable:
            raise HTTPException(status_code=404, detail="소모품을 찾을 수 없습니다.")
        
        # 업데이트할 필드들만 수정
        if consumable_data.name is not None:
            consumable.Name = consumable_data.name
        if consumable_data.description is not None:
            consumable.Description = consumable_data.description
        if consumable_data.release is not None:
            consumable.Release = consumable_data.release
        if consumable_data.unit_type is not None:
            consumable.Unit_Type = consumable_data.unit_type
        if consumable_data.price is not None:
            consumable.Price = consumable_data.price
        if consumable_data.i_value is not None:
            consumable.I_Value = consumable_data.i_value
        if consumable_data.f_value is not None:
            consumable.F_Value = consumable_data.f_value
        # Unit_Price 재계산이 필요한 경우 (price, i_value, f_value가 변경된 경우)
        if any([consumable_data.price is not None, consumable_data.i_value is not None, consumable_data.f_value is not None]):
            # 현재 값들 가져오기
            current_price = consumable.Price
            current_i_value = consumable.I_Value
            current_f_value = consumable.F_Value
            
            # 새로운 값들 적용
            if consumable_data.price is not None:
                current_price = consumable_data.price
            if consumable_data.i_value is not None:
                current_i_value = consumable_data.i_value
            if consumable_data.f_value is not None:
                current_f_value = consumable_data.f_value
            
            # Unit_Price 재계산
            new_unit_price = calculate_unit_price(current_price, current_i_value, current_f_value)
            consumable.Unit_Price = new_unit_price
        
        # 직접 unit_price가 제공된 경우
        if consumable_data.taxable_type is not None:
            consumable.TaxableType = consumable_data.taxable_type
        
        if consumable_data.covered_type is not None:
            consumable.Covered_Type = consumable_data.covered_type
        
        # 직접 unit_price가 제공된 경우
        if consumable_data.unit_price is not None:
            consumable.Unit_Price = consumable_data.unit_price
        
        # VAT 재계산이 필요한 경우 (Unit_Price가 변경되었거나 TaxableType이 변경된 경우)
        if any([consumable_data.price is not None, consumable_data.i_value is not None, 
                consumable_data.f_value is not None, consumable_data.unit_price is not None, 
                consumable_data.taxable_type is not None]):
            # 현재 Unit_Price 가져오기
            current_unit_price = consumable.Unit_Price
            current_taxable_type = consumable.TaxableType
            
            # VAT 재계산
            new_vat = calculate_vat(current_unit_price, current_taxable_type)
            consumable.VAT = new_vat
        
        # Global 설정 조회 (Element 원가 계산에 필요)
        global_settings = db.query(Global).first()
        if not global_settings:
            raise HTTPException(status_code=404, detail="Global 설정을 찾을 수 없습니다.")
        
        # Element Cost에 영향을 주는 필드가 변경된 경우 연쇄 업데이트
        cost_affecting_fields = ['price', 'i_value', 'f_value', 'unit_price']
        has_cost_changes = any(getattr(consumable_data, field) is not None for field in cost_affecting_fields)
        
        if has_cost_changes:
            # 해당 소모품을 사용하는 모든 Element들의 Procedure_Cost 재계산 및 연쇄 업데이트
            update_results = cascade_update_by_consumable(db, consumable_id, global_settings)
        else:
            update_results = {'elements': 0, 'bundles': 0, 'customs': 0, 'sequences': 0, 'products': 0}
        
        db.commit()
        
        return {
            "status": "success",
            "message": "소모품이 성공적으로 업데이트되었습니다.",
            "data": ConsumableResponse.from_orm(consumable),
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
        raise HTTPException(status_code=500, detail=f"소모품 업데이트 중 오류가 발생했습니다: {str(e)}")

@consumables_router.delete("/{consumable_id}")
async def delete_consumable(consumable_id: int, db: Session = Depends(get_db)):
    """Consumables 삭제"""
    # 시나리오: 더 이상 사용하지 않는 소모품을 삭제
    # 구현:
    # 1. 해당 소모품을 사용하는 Element 목록 확인
    # 2. 사용 중인 Element가 있으면 삭제 불가 에러 반환
    # 3. 사용 중이지 않으면 Consumables 삭제
    # 4. 트랜잭션 커밋
    # 영향: 사용 중이지 않은 소모품만 삭제 가능하므로 다른 테이블에 영향 없음
    
    try:
        consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_id,
            Consumables.Release == 1
        ).first()
        
        if not consumable:
            raise HTTPException(status_code=404, detail="소모품을 찾을 수 없습니다.")
        
        # TODO: 해당 소모품을 사용하는 Element 목록 확인
        # TODO: 사용 중인 Element가 있으면 삭제 불가 에러 반환
        
        db.delete(consumable)
        db.commit()
        
        return {
            "status": "success",
            "message": "소모품이 성공적으로 삭제되었습니다."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"소모품 삭제 중 오류가 발생했습니다: {str(e)}")

# ============================================================================
# Release 비활성화/활성화 API
# ============================================================================

@consumables_router.put("/{consumable_id}/deactivate")
async def deactivate_consumable(consumable_id: int, db: Session = Depends(get_db)):
    """Consumables 비활성화"""
    # 1. 해당 소모품을 사용하는 Element 목록 확인
    # 2. 의존성 경고 메시지 반환
    # 3. Consumables 테이블의 Release를 0으로 설정
    
    try:
        consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_id,
            Consumables.Release == 1
        ).first()
        
        if not consumable:
            raise HTTPException(status_code=404, detail="소모품을 찾을 수 없습니다.")
        
        # TODO: 해당 소모품을 사용하는 Element 목록 확인
        # TODO: 의존성 경고 메시지 반환
        
        consumable.Release = 0
        db.commit()
        
        return {
            "status": "success",
            "message": "소모품이 비활성화되었습니다.",
            "warning": "이 소모품을 사용하는 Element들이 있을 수 있습니다."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"소모품 비활성화 중 오류가 발생했습니다: {str(e)}")

@consumables_router.put("/{consumable_id}/activate")
async def activate_consumable(consumable_id: int, db: Session = Depends(get_db)):
    """Consumables 활성화"""
    # Consumables 테이블의 Release를 1로 설정
    
    try:
        consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_id,
            Consumables.Release == 0
        ).first()
        
        if not consumable:
            raise HTTPException(status_code=404, detail="비활성화된 소모품을 찾을 수 없습니다.")
        
        consumable.Release = 1
        db.commit()
        
        return {
            "status": "success",
            "message": "소모품이 활성화되었습니다."
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"소모품 활성화 중 오류가 발생했습니다: {str(e)}")
