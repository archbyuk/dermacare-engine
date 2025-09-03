"""
    Element CRUD API
    
    이 모듈은 Element의 생성, 조회, 수정, 삭제, 비활성화/활성화 기능을 제공합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, validator
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from db.session import get_db
from db.models.procedure import ProcedureElement
from db.models.procedure import ProcedureBundle
from db.models.procedure import ProcedureCustom
from db.models.global_config import Global
from db.models.consumables import Consumables
from .utils import calculate_element_procedure_cost, cascade_update_by_element_obj, update_element_references

# 라우터 설정
elements_router = APIRouter(
    prefix="/admin/elements",
    tags=["Elements"]
)

# ============================================================================
# Pydantic 모델
# ============================================================================

class ElementCreateRequest(BaseModel):
    id: int
    name: str
    class_major: str
    class_sub: str
    class_detail: str
    class_type: str
    description: Optional[str] = None
    position_type: str
    cost_time: float
    plan_state: int = 0
    plan_count: int = 1
    plan_interval: int = -1
    consum_1_id: Optional[int] = None
    consum_1_count: int = 1
    procedure_level: str = "보통"
    price: int
    
    @validator('id')
    def validate_id(cls, v):
        if v < 0:
            raise ValueError('Element ID는 0 이상이어야 합니다.')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Element 이름은 비어있을 수 없습니다.')
        return v.strip()
    
    @validator('cost_time')
    def validate_cost_time(cls, v):
        if v <= 0:
            raise ValueError('Cost Time은 0보다 커야 합니다.')
        return v
    
    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price는 0 이상이어야 합니다.')
        return v
    
    @validator('plan_count')
    def validate_plan_count(cls, v):
        if v <= 0:
            raise ValueError('Plan Count는 0보다 커야 합니다.')
        return v
    
    @validator('consum_1_count')
    def validate_consum_1_count(cls, v):
        if v <= 0:
            raise ValueError('Consum 1 Count는 0보다 커야 합니다.')
        return v

class ElementUpdateRequest(BaseModel):
    # ID 변경 (상위 테이블 참조 업데이트 필요)
    id: Optional[int] = None
    
    # 기본 정보 (Procedure_Cost에 영향 없음)
    name: Optional[str] = None
    class_major: Optional[str] = None
    class_sub: Optional[str] = None
    class_detail: Optional[str] = None
    class_type: Optional[str] = None
    description: Optional[str] = None
    procedure_level: Optional[str] = None
    price: Optional[int] = None
    release: Optional[int] = None
    
    # Procedure_Cost에 직접 영향
    position_type: Optional[str] = None    # 인건비 변경
    cost_time: Optional[float] = None      # 인건비 변경
    plan_state: Optional[int] = None       # 플랜 배수 변경
    plan_count: Optional[int] = None       # 플랜 배수 변경
    consum_1_id: Optional[int] = None      # 소모품비용 변경
    consum_1_count: Optional[int] = None   # 소모품비용 변경
    
    @validator('id')
    def validate_id(cls, v):
        if v is not None and v < 0:
            raise ValueError('Element ID는 0 이상이어야 합니다.')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Element 이름은 비어있을 수 없습니다.')
        return v.strip() if v else v
    
    @validator('cost_time')
    def validate_cost_time(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Cost Time은 0보다 커야 합니다.')
        return v
    
    @validator('price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Price는 0 이상이어야 합니다.')
        return v
    
    @validator('plan_count')
    def validate_plan_count(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Plan Count는 0보다 커야 합니다.')
        return v
    
    @validator('consum_1_count')
    def validate_consum_1_count(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Consum 1 Count는 0보다 커야 합니다.')
        return v

class ElementResponse(BaseModel):
    id: int
    name: Optional[str] = None
    class_major: Optional[str] = None
    class_sub: Optional[str] = None
    class_detail: Optional[str] = None
    class_type: Optional[str] = None
    description: Optional[str] = None
    position_type: Optional[str] = None
    cost_time: Optional[float] = None
    plan_state: Optional[int] = None
    plan_count: Optional[int] = None
    plan_interval: Optional[int] = None
    consum_1_id: Optional[int] = None
    consum_1_name: Optional[str] = None  # 소모품 이름 추가
    consum_1_unit: Optional[str] = None  # 소모품 단위 추가
    consum_1_count: Optional[int] = None
    procedure_level: Optional[str] = None
    procedure_cost: Optional[int] = None
    price: Optional[int] = None
    release: Optional[int] = None

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj, consumable_name=None, consumable_unit=None):
        return cls(
            id=obj.ID,
            name=obj.Name,
            class_major=obj.Class_Major,
            class_sub=obj.Class_Sub,
            class_detail=obj.Class_Detail,
            class_type=obj.Class_Type,
            description=obj.description,
            position_type=obj.Position_Type,
            cost_time=obj.Cost_Time,
            plan_state=obj.Plan_State,
            plan_count=obj.Plan_Count,
            plan_interval=obj.Plan_Interval,
            consum_1_id=obj.Consum_1_ID,
            consum_1_name=consumable_name,  # 소모품 이름 설정
            consum_1_unit=consumable_unit,  # 소모품 단위 설정
            consum_1_count=obj.Consum_1_Count,
            procedure_level=obj.Procedure_Level,
            procedure_cost=obj.Procedure_Cost,
            price=obj.Price,
            release=obj.Release
        )

# ============================================================================
# Element API
# ============================================================================

@elements_router.get("/")
async def get_elements_list(db: Session = Depends(get_db)):
    """Element 목록 조회"""
    # 시나리오: 관리자가 사용 가능한 모든 Element 목록을 확인
    # 구현: Procedure_Element 테이블에서 모든 Element 조회 (Release 상태와 관계없이)
    # 응답: Element ID, 이름, 분류, 시술자 타입, 원가 등 반환
    
    try:
        elements = db.query(ProcedureElement).all()
        
        # 각 Element에 대해 소모품 정보 조회
        element_responses = []
        for element in elements:
            consumable = None
            if element.Consum_1_ID and element.Consum_1_ID != -1:
                consumable = db.query(Consumables).filter(
                    Consumables.ID == element.Consum_1_ID,
                    Consumables.Release == 1
                ).first()
            
            element_responses.append(
                ElementResponse.from_orm(
                    element, 
                    consumable.Name if consumable else None,
                    consumable.Unit_Type if consumable else None
                )
            )
        
        return element_responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Element 목록 조회 중 오류가 발생했습니다: {str(e)}")

@elements_router.get("/{element_id}")
async def get_element_detail(element_id: int, db: Session = Depends(get_db)):
    """Element 상세 조회"""
    # 시나리오: 특정 Element의 상세 정보를 확인
    # 구현: Procedure_Element 테이블에서 특정 Element의 모든 정보 조회 (Release 상태와 관계없이)
    # 응답: Element의 상세 정보 반환
    
    try:
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id
        ).first()
        
        if not element:
            raise HTTPException(status_code=404, detail="Element를 찾을 수 없습니다.")
        
        consumable = None
        if element.Consum_1_ID and element.Consum_1_ID != -1:
            consumable = db.query(Consumables).filter(
                Consumables.ID == element.Consum_1_ID,
                Consumables.Release == 1
            ).first()
        
        return ElementResponse.from_orm(
            element, 
            consumable.Name if consumable else None,
            consumable.Unit_Type if consumable else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Element 상세 조회 중 오류가 발생했습니다: {str(e)}")

@elements_router.post("/")
async def create_element(element_data: ElementCreateRequest, db: Session = Depends(get_db)):
    """Element 생성"""
    # 시나리오: 새로운 Element를 시스템에 추가
    # 구현:
    # 1. ID 중복 체크
    # 2. Global 설정 조회
    # 3. Consumable 조회 (있는 경우)
    # 4. Procedure_Cost 계산
    # 5. Element 생성
    # 영향: 새로 생성된 Element는 아직 사용되지 않으므로 다른 테이블에 영향 없음
    
    try:
        # ID 중복 체크
        existing_element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_data.id
        ).first()
        
        if existing_element:
            raise HTTPException(
                status_code=400, 
                detail=f"ID {element_data.id}는 이미 사용 중입니다. 다른 ID를 사용해주세요."
            )
        
        # Global 설정 조회
        global_settings = db.query(Global).first()
        if not global_settings:
            raise HTTPException(status_code=404, detail="Global 설정을 찾을 수 없습니다.")
        
        # Consumable 조회
        consumable = None
        if element_data.consum_1_id and element_data.consum_1_id != -1:
            consumable = db.query(Consumables).filter(
                Consumables.ID == element_data.consum_1_id,
                Consumables.Release == 1
            ).first()
        
        # Procedure_Cost 계산
        procedure_cost = calculate_element_procedure_cost(
            element_data.position_type,
            element_data.cost_time,
            element_data.consum_1_id or -1,
            element_data.consum_1_count,
            element_data.plan_state,
            element_data.plan_count,
            global_settings,
            consumable
        )
        
        # Element 생성
        new_element = ProcedureElement(
            ID=element_data.id,
            Name=element_data.name,
            Class_Major=element_data.class_major,
            Class_Sub=element_data.class_sub,
            Class_Detail=element_data.class_detail,
            Class_Type=element_data.class_type,
            description=element_data.description,
            Position_Type=element_data.position_type,
            Cost_Time=element_data.cost_time,
            Plan_State=element_data.plan_state,
            Plan_Count=element_data.plan_count,
            Plan_Interval=element_data.plan_interval,
            Consum_1_ID=element_data.consum_1_id,
            Consum_1_Count=element_data.consum_1_count,
            Procedure_Level=element_data.procedure_level,
            Procedure_Cost=procedure_cost,
            Price=element_data.price,
            Release=1
        )
        
        db.add(new_element)
        db.commit()
        db.refresh(new_element)
        
        return {
            "status": "success",
            "message": "Element가 성공적으로 생성되었습니다.",
            "data": ElementResponse.from_orm(new_element)
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Element 생성 중 오류가 발생했습니다: {str(e)}")


# ============================================================================
# 삭제 관련 API
# ============================================================================

from .delete.element import ElementDeletionValidator
from .delete.base import DeletionResponse

@elements_router.get("/{element_id}/deletion-check")
async def check_element_deletion_safety(
    element_id: int, 
    db: Session = Depends(get_db)
):
    """Element 삭제 전 안전성 검증"""
    
    try:
        # Element 존재 여부 확인
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id
        ).first()
        
        if not element:
            raise HTTPException(
                status_code=404, 
                detail=f"Element ID {element_id}를 찾을 수 없습니다."
            )
        
        # 삭제 안전성 검증
        validator = ElementDeletionValidator()
        result = validator.validate_deletion(element_id, db)
        
        return DeletionResponse(
            status="success",
            message="Element 삭제 안전성 검증 완료",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Element 삭제 검증 중 오류가 발생했습니다: {str(e)}"
        )

@elements_router.delete("/{element_id}")
async def delete_element(
    element_id: int,
    force: bool = Query(False, description="강제 삭제 (참조 관계 무시)"),
    db: Session = Depends(get_db)
):
    """Element 삭제"""
    
    try:
        # Element 존재 여부 확인
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id
        ).first()
        
        if not element:
            raise HTTPException(
                status_code=404, 
                detail=f"Element ID {element_id}를 찾을 수 없습니다."
            )
        
        # 강제 삭제가 아닌 경우 안전성 검증
        if not force:
            validator = ElementDeletionValidator()
            result = validator.validate_deletion(element_id, db)
            
            if not result.is_deletable:
                return DeletionResponse(
                    status="error",
                    message="Element를 삭제할 수 없습니다. 다른 곳에서 사용 중입니다.",
                    data=result
                )
        
        # 삭제 실행
        validator = ElementDeletionValidator()
        success = validator.execute_deletion(element_id, db, force=force)
        
        if success:
            return {
                "status": "success",
                "message": f"Element ID {element_id}가 성공적으로 삭제되었습니다."
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Element 삭제에 실패했습니다."
            )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Element 삭제 중 오류가 발생했습니다: {str(e)}"
        )

@elements_router.put("/{element_id}/deactivate")
async def deactivate_element(element_id: int, db: Session = Depends(get_db)):
    """Element 비활성화"""
    # 시나리오: Element를 비활성화하여 사용하지 않도록 설정
    # 구현: Procedure_Element 테이블의 Release를 0으로 설정
    # 영향: 비활성화된 Element는 조회되지 않지만 데이터는 유지
    
    try:
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id,
            ProcedureElement.Release == 1
        ).first()
        
        if not element:
            raise HTTPException(status_code=404, detail="Element를 찾을 수 없습니다.")
        
        element.Release = 0
        db.commit()
        
        return {
            "status": "success",
            "message": "Element가 비활성화되었습니다.",
            "warning": "이 Element를 사용하는 상위 테이블들이 있을 수 있습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Element 비활성화 중 오류가 발생했습니다: {str(e)}")

@elements_router.put("/{element_id}/activate")
async def activate_element(element_id: int, db: Session = Depends(get_db)):
    """Element 활성화"""
    # 시나리오: 비활성화된 Element를 다시 활성화
    # 구현: Procedure_Element 테이블의 Release를 1로 설정
    # 영향: 활성화된 Element는 다시 조회되고 사용 가능
    
    try:
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id,
            ProcedureElement.Release == 0
        ).first()
        
        if not element:
            raise HTTPException(status_code=404, detail="비활성화된 Element를 찾을 수 없습니다.")
        
        element.Release = 1
        db.commit()
        
        return {
            "status": "success",
            "message": "Element가 활성화되었습니다."
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Element 활성화 중 오류가 발생했습니다: {str(e)}")

@elements_router.put("/{element_id}")
async def update_element(element_id: int, element_data: ElementUpdateRequest, db: Session = Depends(get_db)):
    """Element 수정 (상위 테이블 연쇄 업데이트)"""
    try:
        # 1. Element ID 검증
        if element_id <= 0:
            raise HTTPException(status_code=400, detail="Element ID는 0보다 커야 합니다.")
        
        # 2. 기존 Element 조회
        existing_element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id
        ).first()
        
        if not existing_element:
            raise HTTPException(status_code=404, detail="Element를 찾을 수 없습니다.")
        
        # 3. ID 변경 처리
        new_element_id = element_id
        if element_data.id is not None and element_data.id != element_id:
            # 새로운 ID 중복 확인
            existing_new_id = db.query(ProcedureElement).filter(
                ProcedureElement.ID == element_data.id
            ).first()
            
            if existing_new_id:
                raise HTTPException(
                    status_code=400, 
                    detail=f"ID {element_data.id}는 이미 사용 중입니다."
                )
            
            new_element_id = element_data.id
        
        # 4. Global 설정 조회
        global_settings = db.query(Global).first()
        if not global_settings:
            raise HTTPException(status_code=404, detail="Global 설정을 찾을 수 없습니다.")
        
        # 5. Consumable 조회 (변경된 경우)
        consumable = None
        consumable_id = element_data.consum_1_id if element_data.consum_1_id is not None else existing_element.Consum_1_ID
        if consumable_id and consumable_id != -1:
            consumable = db.query(Consumables).filter(
                Consumables.ID == consumable_id,
                Consumables.Release == 1
            ).first()
        
        # 6. Element 데이터 업데이트
        if element_data.name is not None:
            existing_element.Name = element_data.name
        if element_data.class_major is not None:
            existing_element.Class_Major = element_data.class_major
        if element_data.class_sub is not None:
            existing_element.Class_Sub = element_data.class_sub
        if element_data.class_detail is not None:
            existing_element.Class_Detail = element_data.class_detail
        if element_data.class_type is not None:
            existing_element.Class_Type = element_data.class_type
        if element_data.description is not None:
            existing_element.description = element_data.description
        if element_data.procedure_level is not None:
            existing_element.Procedure_Level = element_data.procedure_level
        if element_data.price is not None:
            existing_element.Price = element_data.price
        if element_data.release is not None:
            existing_element.Release = element_data.release
        
        # Procedure_Cost에 영향을 주는 필드들
        cost_changed = False
        if element_data.position_type is not None:
            existing_element.Position_Type = element_data.position_type
            cost_changed = True
        if element_data.cost_time is not None:
            existing_element.Cost_Time = element_data.cost_time
            cost_changed = True
        if element_data.plan_state is not None:
            existing_element.Plan_State = element_data.plan_state
            cost_changed = True
        if element_data.plan_count is not None:
            existing_element.Plan_Count = element_data.plan_count
            cost_changed = True
        if element_data.consum_1_id is not None:
            existing_element.Consum_1_ID = element_data.consum_1_id
            cost_changed = True
        if element_data.consum_1_count is not None:
            existing_element.Consum_1_Count = element_data.consum_1_count
            cost_changed = True
        
        # 7. Procedure_Cost 재계산 (비용 관련 필드가 변경된 경우)
        if cost_changed:
            existing_element.Procedure_Cost = calculate_element_procedure_cost(
                existing_element.Position_Type,
                existing_element.Cost_Time,
                existing_element.Plan_State,
                existing_element.Plan_Count,
                existing_element.Consum_1_ID,
                existing_element.Consum_1_Count,
                global_settings,
                consumable
            )
        
        # 8. ID 변경 시 참조 테이블 업데이트
        if new_element_id != element_id:
            try:
                # 기존 Element를 새 ID로 복사
                new_element = ProcedureElement(
                    ID=new_element_id,
                    Release=existing_element.Release,
                    Class_Major=existing_element.Class_Major,
                    Class_Sub=existing_element.Class_Sub,
                    Class_Detail=existing_element.Class_Detail,
                    Class_Type=existing_element.Class_Type,
                    Name=existing_element.Name,
                    description=existing_element.description,
                    Position_Type=existing_element.Position_Type,
                    Cost_Time=existing_element.Cost_Time,
                    Plan_State=existing_element.Plan_State,
                    Plan_Count=existing_element.Plan_Count,
                    Plan_Interval=existing_element.Plan_Interval,
                    Consum_1_ID=existing_element.Consum_1_ID,
                    Consum_1_Count=existing_element.Consum_1_Count,
                    Procedure_Level=existing_element.Procedure_Level,
                    Procedure_Cost=existing_element.Procedure_Cost,
                    Price=existing_element.Price
                )
                
                db.add(new_element)
                
                # 상위 테이블들의 Element_ID 참조 업데이트
                update_results = update_element_references(element_id, new_element_id, db)
                
                # 기존 Element 삭제
                db.delete(existing_element)
                
                print(f"Element ID 변경 연쇄 업데이트 결과: {update_results}")
                
            except Exception as cascade_error:
                # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
                print(f"Element ID 변경 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        # 9. 트랜잭션 커밋
        db.commit()
        
        # 10. 연쇄 업데이트 실행 (별도 트랜잭션)
        try:
            # ID가 변경된 경우 새 ID로, 아니면 기존 ID로
            target_element_id = new_element_id if new_element_id != element_id else element_id
            target_element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == target_element_id
            ).first()
            
            if target_element:
                cascade_results = cascade_update_by_element_obj(target_element, db)
                print(f"Element 수정 후 연쇄 업데이트 결과: {cascade_results}")
        except Exception as cascade_error:
            # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
            print(f"Element 수정 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        # 11. 수정된 Element 조회하여 반환
        return await get_element_detail(target_element_id, db)
        
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"데이터 무결성 오류: {str(e)}")
    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Element 수정 중 오류가 발생했습니다: {str(e)}")
