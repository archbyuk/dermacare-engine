"""
    Custom CRUD API
    
    이 모듈은 Custom의 생성, 조회, 수정, 삭제 기능을 제공합니다.
    GroupID 기반으로 커스텀 시술들을 관리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from pydantic import BaseModel, validator

from db.session import get_db
from db.models.procedure import ProcedureCustom, ProcedureElement
from db.models.global_config import Global
from db.models.consumables import Consumables
from .utils import calculate_element_procedure_cost, cascade_update_by_custom_group, cascade_update_custom_group_id

# 라우터 설정
customs_router = APIRouter(
    prefix="/admin/customs",
    tags=["Customs"]
)

# ============================================================================
# Pydantic 모델
# ============================================================================

class CustomElementRequest(BaseModel):
    element_id: int
    custom_count: int = 1
    element_limit: Optional[int] = None
    price_ratio: float = 1.0
    
    @validator('element_id')
    def validate_element_id(cls, v):
        if v <= 0:
            raise ValueError('Element ID는 0보다 커야 합니다.')
        return v
    
    @validator('custom_count')
    def validate_custom_count(cls, v):
        if v <= 0:
            raise ValueError('Custom Count는 0보다 커야 합니다.')
        return v
    
    @validator('element_limit')
    def validate_element_limit(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Element Limit는 0보다 커야 합니다.')
        return v
    
    @validator('price_ratio')
    def validate_price_ratio(cls, v):
        if v <= 0 or v > 1:
            raise ValueError('Price Ratio는 0과 1 사이의 값이어야 합니다.')
        return v

class CustomCreateRequest(BaseModel):
    group_id: int
    name: str
    description: Optional[str] = None
    release: int = 1
    elements: List[CustomElementRequest]
    
    @validator('group_id')
    def validate_group_id(cls, v):
        if v <= 0:
            raise ValueError('Group ID는 0보다 커야 합니다.')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Custom 이름은 비어있을 수 없습니다.')
        return v.strip()
    
    @validator('elements')
    def validate_elements(cls, v):
        if not v:
            raise ValueError('Custom에는 최소 하나의 Element가 포함되어야 합니다.')
        if len(v) > 10:  # 최대 10개 Element 제한
            raise ValueError('Custom에는 최대 10개의 Element만 포함할 수 있습니다.')
        return v

class CustomUpdateRequest(BaseModel):
    group_id: Optional[int] = None  # Group ID 변경 지원 추가
    name: Optional[str] = None
    description: Optional[str] = None
    release: Optional[int] = None
    elements: Optional[List[CustomElementRequest]] = None
    
    @validator('group_id')
    def validate_group_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Group ID는 0보다 커야 합니다.')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Custom 이름은 비어있을 수 없습니다.')
        return v.strip() if v else v
    
    @validator('elements')
    def validate_elements(cls, v):
        if v is not None:
            if not v:
                raise ValueError('Custom에는 최소 하나의 Element가 포함되어야 합니다.')
            if len(v) > 10:
                raise ValueError('Custom에는 최대 10개의 Element만 포함할 수 있습니다.')
        return v

# Element 상세 정보를 포함하는 Response 모델 추가
class ElementDetailResponse(BaseModel):
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
    consum_1_name: Optional[str] = None
    consum_1_unit: Optional[str] = None
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
            consum_1_name=consumable_name,
            consum_1_unit=consumable_unit,
            consum_1_count=obj.Consum_1_Count,
            procedure_level=obj.Procedure_Level,
            procedure_cost=obj.Procedure_Cost,
            price=obj.Price,
            release=obj.Release
        )

class CustomElementResponse(BaseModel):
    id: int
    group_id: int
    element_id: int
    custom_count: Optional[int] = None  # NULL 허용
    element_limit: Optional[int] = None
    element_cost: Optional[int] = None
    price_ratio: float
    release: int = 1
    element_detail: Optional[ElementDetailResponse] = None  # Element 상세 정보 추가

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj, element_detail=None):
        return cls(
            id=obj.ID,
            group_id=obj.GroupID,
            element_id=obj.Element_ID,
            custom_count=obj.Custom_Count,
            element_limit=obj.Element_Limit,
            element_cost=obj.Element_Cost,
            price_ratio=obj.Price_Ratio,
            release=obj.Release,
            element_detail=element_detail
        )

class CustomResponse(BaseModel):
    group_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    release: int = 1
    elements: List[CustomElementResponse] = []

    class Config:
        from_attributes = True

# ============================================================================
# 트랜잭션 헬퍼 함수들
# ============================================================================

def validate_custom_elements(elements: List[CustomElementRequest], db: Session) -> List[ProcedureElement]:
    """
    Custom Elements의 유효성을 검증하고 Element 객체들을 반환합니다.
    
    Args:
        elements: 검증할 Element 요청 리스트
        db: 데이터베이스 세션
    
    Returns:
        List[ProcedureElement]: 검증된 Element 객체 리스트
    
    Raises:
        HTTPException: 검증 실패 시
    """
    validated_elements = []
    
    for element_data in elements:
        # Element 존재 확인
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_data.element_id,
            ProcedureElement.Release == 1
        ).first()
        
        if not element:
            raise HTTPException(
                status_code=404, 
                detail=f"Element ID {element_data.element_id}를 찾을 수 없습니다."
            )
        
        validated_elements.append(element)
    
    return validated_elements

def calculate_custom_element_costs(elements: List[ProcedureElement], custom_counts: List[int], db: Session) -> List[int]:
    """
    Custom Elements의 비용을 계산합니다.
    
    Args:
        elements: Element 객체 리스트
        custom_counts: Custom Count 리스트
        db: 데이터베이스 세션
    
    Returns:
        List[int]: 계산된 비용 리스트
    """
    # Global 설정 조회
    global_settings = db.query(Global).first()
    if not global_settings:
        raise HTTPException(status_code=404, detail="Global 설정을 찾을 수 없습니다.")
    
    costs = []
    for element, custom_count in zip(elements, custom_counts):
        # Consumable 조회
        consumable = None
        if element.Consum_1_ID and element.Consum_1_ID != -1:
            consumable = db.query(Consumables).filter(
                Consumables.ID == element.Consum_1_ID,
                Consumables.Release == 1
            ).first()
        
        # Element_Cost 계산 (Custom Count 적용)
        base_cost = calculate_element_procedure_cost(
            element.Position_Type,
            element.Cost_Time,
            element.Consum_1_ID or -1,
            element.Consum_1_Count,
            element.Plan_State,
            element.Plan_Count,
            global_settings,
            consumable
        )
        
        # Custom Count를 적용한 최종 비용
        final_cost = base_cost * custom_count
        costs.append(final_cost)
    
    return costs

def create_custom_records(
    group_id: int, 
    name: str, 
    description: Optional[str], 
    release: int,
    elements: List[ProcedureElement],
    costs: List[int],
    custom_counts: List[int],
    element_limits: List[Optional[int]],
    price_ratios: List[float],
    db: Session
) -> List[ProcedureCustom]:
    """
    Custom 레코드들을 생성합니다.
    
    Args:
        group_id: Custom Group ID
        name: Custom 이름
        description: Custom 설명
        release: 활성화 상태
        elements: Element 객체 리스트
        costs: 계산된 비용 리스트
        custom_counts: Custom Count 리스트
        element_limits: Element Limit 리스트
        price_ratios: 가격 비율 리스트
        db: 데이터베이스 세션
    
    Returns:
        List[ProcedureCustom]: 생성된 Custom 객체 리스트
    """
    customs = []
    
    for i, (element, cost, custom_count, element_limit, price_ratio) in enumerate(
        zip(elements, costs, custom_counts, element_limits, price_ratios), 1
    ):
        custom = ProcedureCustom(
            GroupID=group_id,
            ID=i,
            Release=release,
            Name=name,
            Description=description,
            Element_ID=element.ID,
            Custom_Count=custom_count,
            Element_Limit=element_limit,
            Element_Cost=cost,
            Price_Ratio=price_ratio,
        )
        
        db.add(custom)
        customs.append(custom)
    
    return customs

# ============================================================================
# API 엔드포인트
# ============================================================================

@customs_router.get("/")
async def get_customs_list(db: Session = Depends(get_db)):
    """Custom 목록 조회 (GroupID별로 그룹화)"""
    try:
        # 모든 Custom 조회 (Release 상태와 관계없이)
        customs = db.query(ProcedureCustom).order_by(ProcedureCustom.GroupID, ProcedureCustom.ID).all()
        
        # GroupID별로 그룹화
        custom_groups = {}
        for custom in customs:
            if custom.GroupID not in custom_groups:
                custom_groups[custom.GroupID] = {
                    'group_id': custom.GroupID,
                    'name': custom.Name,
                    'description': custom.Description,
                    'release': custom.Release,
                    'elements': []
                }
            
            custom_groups[custom.GroupID]['elements'].append(
                CustomElementResponse.from_orm(custom)
            )
        
        return list(custom_groups.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom 목록 조회 중 오류가 발생했습니다: {str(e)}")

@customs_router.get("/{group_id}")
async def get_custom(group_id: int, db: Session = Depends(get_db)):
    """특정 Custom 조회 (GroupID 기준)"""
    try:
        # Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 해당 GroupID의 모든 Custom 조회 (Release 상태와 관계없이)
        customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.GroupID == group_id
        ).order_by(ProcedureCustom.ID).all()
        
        if not customs:
            raise HTTPException(status_code=404, detail="Custom을 찾을 수 없습니다.")
        
        # Custom 요소들을 Element 상세 정보와 함께 구성
        custom_elements = []
        for custom in customs:
            # Element 상세 정보 조회
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == custom.Element_ID
            ).first()
            
            element_detail = None
            if element:
                # Element의 소모품 정보 조회
                consumable = None
                if element.Consum_1_ID and element.Consum_1_ID != -1:
                    consumable = db.query(Consumables).filter(
                        Consumables.ID == element.Consum_1_ID,
                        Consumables.Release == 1
                    ).first()
                
                element_detail = ElementDetailResponse.from_orm(
                    element,
                    consumable.Name if consumable else None,
                    consumable.Unit_Type if consumable else None
                )
            
            custom_elements.append(
                CustomElementResponse.from_orm(custom, element_detail)
            )
        
        # 첫 번째 Custom에서 그룹 정보 가져오기
        first_custom = customs[0]
        custom_response = CustomResponse(
            group_id=first_custom.GroupID,
            name=first_custom.Name,
            description=first_custom.Description,
            release=first_custom.Release,
            elements=custom_elements
        )
        
        return custom_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Custom 조회 중 오류가 발생했습니다: {str(e)}")

@customs_router.post("/")
async def create_custom(custom_data: CustomCreateRequest, db: Session = Depends(get_db)):
    """Custom 생성"""
    try:
        # 1. GroupID 중복 확인
        existing_custom = db.query(ProcedureCustom).filter(
            ProcedureCustom.GroupID == custom_data.group_id,
            ProcedureCustom.Release == 1
        ).first()
        
        if existing_custom:
            raise HTTPException(
                status_code=400, 
                detail=f"GroupID {custom_data.group_id}는 이미 사용 중입니다."
            )
        
        # 2. Elements 검증 및 비용 계산
        elements = validate_custom_elements(custom_data.elements, db)
        custom_counts = [elem.custom_count for elem in custom_data.elements]
        element_limits = [elem.element_limit for elem in custom_data.elements]
        price_ratios = [elem.price_ratio for elem in custom_data.elements]
        
        costs = calculate_custom_element_costs(elements, custom_counts, db)
        
        # 3. Custom 레코드 생성
        customs = create_custom_records(
            custom_data.group_id,
            custom_data.name,
            custom_data.description,
            custom_data.release,
            elements,
            costs,
            custom_counts,
            element_limits,
            price_ratios,
            db
        )
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        # 5. 연쇄 업데이트는 불필요 (Custom은 기존 Element 조합이므로)
        # Custom 생성 시에는 상위 테이블 업데이트가 필요하지 않음
        
        # 6. 생성된 Custom 조회하여 반환
        return await get_custom(custom_data.group_id, db)
        
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
        raise HTTPException(status_code=500, detail=f"Custom 생성 중 오류가 발생했습니다: {str(e)}")

@customs_router.put("/{group_id}")
async def update_custom(group_id: int, custom_data: CustomUpdateRequest, db: Session = Depends(get_db)):
    """Custom 수정"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 기존 Custom 조회
        existing_customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.GroupID == group_id,
            ProcedureCustom.Release == 1
        ).all()
        
        if not existing_customs:
            raise HTTPException(status_code=404, detail="Custom을 찾을 수 없습니다.")
        
        # 3. Group ID 변경 처리
        new_group_id = group_id
        if custom_data.group_id is not None and custom_data.group_id != group_id:
            # 새로운 Group ID 중복 확인
            existing_new_group = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == custom_data.group_id,
                ProcedureCustom.Release == 1
            ).first()
            
            if existing_new_group:
                raise HTTPException(
                    status_code=400, 
                    detail=f"GroupID {custom_data.group_id}는 이미 사용 중입니다."
                )
            
            new_group_id = custom_data.group_id
        
        # 4. Custom 정보 업데이트 (첫 번째 Custom에만 적용)
        first_custom = existing_customs[0]
        if custom_data.name is not None:
            first_custom.Name = custom_data.name
        if custom_data.description is not None:
            first_custom.Description = custom_data.description
        if custom_data.release is not None:
            first_custom.Release = custom_data.release
        
        # 5. Elements 업데이트 (제공된 경우)
        if custom_data.elements is not None:
            # 5-1. Elements 검증 및 비용 계산
            elements = validate_custom_elements(custom_data.elements, db)
            custom_counts = [elem.custom_count for elem in custom_data.elements]
            element_limits = [elem.element_limit for elem in custom_data.elements]
            price_ratios = [elem.price_ratio for elem in custom_data.elements]
            
            costs = calculate_custom_element_costs(elements, custom_counts, db)
            
            # 5-2. 기존 Elements 삭제
            for custom in existing_customs:
                db.delete(custom)
            
            # 5-3. 새로운 Elements 생성
            customs = create_custom_records(
                new_group_id,  # 새로운 Group ID 사용
                first_custom.Name,
                first_custom.Description,
                first_custom.Release,
                elements,
                costs,
                custom_counts,
                element_limits,
                price_ratios,
                db
            )
        
        # 6. Group ID 변경 시 참조 테이블 업데이트
        if new_group_id != group_id:
            try:
                cascade_update_custom_group_id(group_id, new_group_id, db)
            except Exception as cascade_error:
                # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
                print(f"Custom Group ID 변경 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        # 7. 트랜잭션 커밋
        db.commit()
        
        # 8. 연쇄 업데이트 실행 (별도 트랜잭션)
        try:
            cascade_update_by_custom_group(new_group_id, db)  # 새로운 Group ID 사용
        except Exception as cascade_error:
            # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
            print(f"Custom 수정 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        # 9. 수정된 Custom 조회하여 반환
        return await get_custom(new_group_id, db)  # 새로운 Group ID 사용
        
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
        raise HTTPException(status_code=500, detail=f"Custom 수정 중 오류가 발생했습니다: {str(e)}")

@customs_router.delete("/{group_id}")
async def delete_custom(group_id: int, db: Session = Depends(get_db)):
    """Custom 삭제"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 해당 GroupID의 모든 Custom 조회
        customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.GroupID == group_id,
            ProcedureCustom.Release == 1
        ).all()
        
        if not customs:
            raise HTTPException(status_code=404, detail="Custom을 찾을 수 없습니다.")
        
        # 3. Sequence에서 참조 확인
        from db.models.procedure import ProcedureSequence
        sequence_count = db.query(ProcedureSequence).filter(
            ProcedureSequence.Custom_ID == group_id,
            ProcedureSequence.Release == 1
        ).count()
        
        if sequence_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"이 Custom은 {sequence_count}개의 Sequence에서 사용 중입니다. 먼저 참조를 제거해주세요."
            )
        
        # 4. Product에서 참조 확인
        from db.models.product import ProductStandard, ProductEvent
        product_standard_count = db.query(ProductStandard).filter(
            ProductStandard.Custom_ID == group_id,
            ProductStandard.Release == 1
        ).count()
        
        product_event_count = db.query(ProductEvent).filter(
            ProductEvent.Custom_ID == group_id,
            ProductEvent.Release == 1
        ).count()
        
        if product_standard_count > 0 or product_event_count > 0:
            total_count = product_standard_count + product_event_count
            raise HTTPException(
                status_code=400, 
                detail=f"이 Custom은 {total_count}개의 Product에서 사용 중입니다. 먼저 참조를 제거해주세요."
            )
        
        # 5. Custom 삭제
        for custom in customs:
            db.delete(custom)
        
        # 6. 트랜잭션 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": f"Custom GroupID {group_id}가 성공적으로 삭제되었습니다."
        }
        
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
        raise HTTPException(status_code=500, detail=f"Custom 삭제 중 오류가 발생했습니다: {str(e)}")

@customs_router.put("/{group_id}/deactivate")
async def deactivate_custom(group_id: int, db: Session = Depends(get_db)):
    """Custom 비활성화"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. Custom 조회
        customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.GroupID == group_id,
            ProcedureCustom.Release == 1
        ).all()
        
        if not customs:
            raise HTTPException(status_code=404, detail="Custom을 찾을 수 없습니다.")
        
        # 3. Custom 비활성화
        for custom in customs:
            custom.Release = 0
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": f"Custom GroupID {group_id}가 비활성화되었습니다."
        }
        
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
        raise HTTPException(status_code=500, detail=f"Custom 비활성화 중 오류가 발생했습니다: {str(e)}")

@customs_router.put("/{group_id}/activate")
async def activate_custom(group_id: int, db: Session = Depends(get_db)):
    """Custom 활성화"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 비활성화된 Custom 조회
        customs = db.query(ProcedureCustom).filter(
            ProcedureCustom.GroupID == group_id,
            ProcedureCustom.Release == 0
        ).all()
        
        if not customs:
            raise HTTPException(status_code=404, detail="비활성화된 Custom을 찾을 수 없습니다.")
        
        # 3. Custom 활성화
        for custom in customs:
            custom.Release = 1
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        # 5. 연쇄 업데이트 실행 (별도 트랜잭션)
        try:
            cascade_update_by_custom_group(group_id, db)
        except Exception as cascade_error:
            # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
            print(f"Custom 활성화 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        return {
            "status": "success",
            "message": f"Custom GroupID {group_id}가 활성화되었습니다."
        }
        
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
        raise HTTPException(status_code=500, detail=f"Custom 활성화 중 오류가 발생했습니다: {str(e)}")
