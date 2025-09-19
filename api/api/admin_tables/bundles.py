"""
    Bundle CRUD API
    
    이 모듈은 Bundle의 생성, 조회, 수정, 삭제 기능을 제공합니다.
    GroupID 기반으로 번들과 요소들을 관리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from pydantic import BaseModel, validator

from db.session import get_db
from db.models.procedure import ProcedureBundle, ProcedureElement
from db.models.global_config import Global
from db.models.consumables import Consumables
from .utils import calculate_element_procedure_cost, cascade_update_by_element_obj, cascade_update_by_bundle_group, cascade_update_bundle_group_id

# 라우터 설정
bundles_router = APIRouter(
    prefix="/bundles",
    tags=["Bundles"]
)

# ============================================================================
# Pydantic 모델
# ============================================================================

class BundleElementRequest(BaseModel):
    element_id: int
    price_ratio: Optional[float] = 1.0  # NULL 허용, 기본값 1.0
    
    @validator('element_id')
    def validate_element_id(cls, v):
        if v <= 0:
            raise ValueError('Element ID는 0보다 커야 합니다.')
        return v
    
    @validator('price_ratio')
    def validate_price_ratio(cls, v):
        if v is not None and (v <= 0 or v > 1):
            raise ValueError('Price Ratio는 0과 1 사이의 값이어야 합니다.')
        return v

class BundleCreateRequest(BaseModel):
    group_id: int
    name: str
    description: Optional[str] = None
    release: int = 1
    elements: List[BundleElementRequest]
    
    @validator('group_id')
    def validate_group_id(cls, v):
        if v <= 0:
            raise ValueError('Group ID는 0보다 커야 합니다.')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Bundle 이름은 비어있을 수 없습니다.')
        return v.strip()
    
    @validator('elements')
    def validate_elements(cls, v):
        if not v:
            raise ValueError('Bundle에는 최소 하나의 Element가 포함되어야 합니다.')
        if len(v) > 10:  # 최대 10개 Element 제한
            raise ValueError('Bundle에는 최대 10개의 Element만 포함할 수 있습니다.')
        return v

class BundleUpdateRequest(BaseModel):
    group_id: Optional[int] = None  # Group ID 변경 지원 추가
    name: Optional[str] = None
    description: Optional[str] = None
    release: Optional[int] = None
    elements: Optional[List[BundleElementRequest]] = None
    
    @validator('group_id')
    def validate_group_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Group ID는 0보다 커야 합니다.')
        return v
    
    @validator('name')
    def validate_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('Bundle 이름은 비어있을 수 없습니다.')
        return v.strip() if v else v
    
    @validator('elements')
    def validate_elements(cls, v):
        if v is not None:
            if not v:
                raise ValueError('Bundle에는 최소 하나의 Element가 포함되어야 합니다.')
            if len(v) > 10:
                raise ValueError('Bundle에는 최대 10개의 Element만 포함할 수 있습니다.')
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

class BundleElementResponse(BaseModel):
    id: int
    group_id: int
    element_id: int
    element_cost: Optional[int] = None
    price_ratio: Optional[float] = None  # NULL 허용
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
            element_cost=obj.Element_Cost,
            price_ratio=obj.Price_Ratio,
            release=obj.Release,
            element_detail=element_detail
        )

class BundleResponse(BaseModel):
    group_id: int
    name: Optional[str] = None
    description: Optional[str] = None
    release: int = 1
    elements: List[BundleElementResponse] = []

    class Config:
        from_attributes = True

# ============================================================================
# 트랜잭션 헬퍼 함수들
# ============================================================================

def validate_bundle_elements(elements: List[BundleElementRequest], db: Session) -> List[ProcedureElement]:
    """
    Bundle Elements의 유효성을 검증하고 Element 객체들을 반환합니다.
    
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

def calculate_bundle_element_costs(elements: List[ProcedureElement], db: Session) -> List[int]:
    """
    Bundle Elements의 비용을 계산합니다.
    
    Args:
        elements: Element 객체 리스트
        db: 데이터베이스 세션
    
    Returns:
        List[int]: 계산된 비용 리스트
    """
    # Global 설정 조회
    global_settings = db.query(Global).first()
    if not global_settings:
        raise HTTPException(status_code=404, detail="Global 설정을 찾을 수 없습니다.")
    
    costs = []
    for element in elements:
        # Consumable 조회
        consumable = None
        if element.Consum_1_ID and element.Consum_1_ID != -1:
            consumable = db.query(Consumables).filter(
                Consumables.ID == element.Consum_1_ID,
                Consumables.Release == 1
            ).first()
        
        # Element_Cost 계산
        cost = calculate_element_procedure_cost(
            element.Position_Type,
            element.Cost_Time,
            element.Consum_1_ID or -1,
            element.Consum_1_Count,
            element.Plan_State,
            element.Plan_Count,
            global_settings,
            consumable
        )
        
        costs.append(cost)
    
    return costs

def create_bundle_records(
    group_id: int, 
    name: str, 
    description: Optional[str], 
    release: int,
    elements: List[ProcedureElement],
    costs: List[int],
    price_ratios: List[float],
    db: Session
) -> List[ProcedureBundle]:
    """
    Bundle 레코드들을 생성합니다.
    
    Args:
        group_id: Bundle Group ID
        name: Bundle 이름
        description: Bundle 설명
        release: 활성화 상태
        elements: Element 객체 리스트
        costs: 계산된 비용 리스트
        price_ratios: 가격 비율 리스트
        db: 데이터베이스 세션
    
    Returns:
        List[ProcedureBundle]: 생성된 Bundle 객체 리스트
    """
    bundles = []
    
    for i, (element, cost, price_ratio) in enumerate(zip(elements, costs, price_ratios), 1):
        bundle = ProcedureBundle(
            GroupID=group_id,
            ID=i,
            Release=release,
            Name=name,
            Description=description,
            Element_ID=element.ID,
            Element_Cost=cost,
            Price_Ratio=price_ratio,
        )
        
        db.add(bundle)
        bundles.append(bundle)
    
    return bundles

# ============================================================================
# API 엔드포인트
# ============================================================================

@bundles_router.get("/")
async def get_bundles_list(db: Session = Depends(get_db)):
    """Bundle 목록 조회 (GroupID별로 그룹화)"""
    try:
        # 모든 Bundle 조회 (Release 상태와 관계없이)
        bundles = db.query(ProcedureBundle).order_by(ProcedureBundle.GroupID, ProcedureBundle.ID).all()
        
        # GroupID별로 그룹화
        bundle_groups = {}
        for bundle in bundles:
            if bundle.GroupID not in bundle_groups:
                bundle_groups[bundle.GroupID] = {
                    'group_id': bundle.GroupID,
                    'name': bundle.Name,
                    'description': bundle.Description,
                    'release': bundle.Release,
                    'elements': []
                }
            
            bundle_groups[bundle.GroupID]['elements'].append(
                BundleElementResponse.from_orm(bundle)
            )
        
        return list(bundle_groups.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bundle 목록 조회 중 오류가 발생했습니다: {str(e)}")

@bundles_router.get("/{group_id}")
async def get_bundle(group_id: int, db: Session = Depends(get_db)):
    """특정 Bundle 조회 (GroupID 기준)"""
    try:
        # Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # N+1 쿼리 문제 해결: LEFT JOIN을 사용하여 한 번의 쿼리로 모든 데이터 조회
        bundles_with_details = db.query(
            ProcedureBundle,
            ProcedureElement,
            Consumables
        ).outerjoin(
            ProcedureElement,
            ProcedureElement.ID == ProcedureBundle.Element_ID
        ).outerjoin(
            Consumables,
            and_(
                Consumables.ID == ProcedureElement.Consum_1_ID,
                Consumables.Release == 1
            )
        ).filter(
            ProcedureBundle.GroupID == group_id
        ).order_by(ProcedureBundle.ID).all()
        
        if not bundles_with_details:
            raise HTTPException(status_code=404, detail="Bundle을 찾을 수 없습니다.")
        
        # Bundle 요소들을 Element 상세 정보와 함께 구성
        bundle_elements = []
        for bundle, element, consumable in bundles_with_details:
            element_detail = None
            if element:
                element_detail = ElementDetailResponse.from_orm(
                    element,
                    consumable.Name if consumable else None,
                    consumable.Unit_Type if consumable else None
                )
            
            bundle_elements.append(
                BundleElementResponse.from_orm(bundle, element_detail)
            )
        
        # 첫 번째 Bundle에서 그룹 정보 가져오기
        first_bundle = bundles_with_details[0][0]  # 첫 번째 튜플의 첫 번째 요소 (ProcedureBundle)
        bundle_response = BundleResponse(
            group_id=first_bundle.GroupID,
            name=first_bundle.Name,
            description=first_bundle.Description,
            release=first_bundle.Release,
            elements=bundle_elements
        )
        
        return bundle_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Bundle 조회 중 오류가 발생했습니다: {str(e)}")

@bundles_router.post("/")
async def create_bundle(bundle_data: BundleCreateRequest, db: Session = Depends(get_db)):
    """Bundle 생성"""
    try:
        # 1. GroupID 중복 확인
        existing_bundle = db.query(ProcedureBundle).filter(
            ProcedureBundle.GroupID == bundle_data.group_id,
            ProcedureBundle.Release == 1
        ).first()
        
        if existing_bundle:
            raise HTTPException(
                status_code=400, 
                detail=f"GroupID {bundle_data.group_id}는 이미 사용 중입니다."
            )
        
        # 2. Elements 검증 및 비용 계산
        elements = validate_bundle_elements(bundle_data.elements, db)
        costs = calculate_bundle_element_costs(elements, db)
        price_ratios = [elem.price_ratio for elem in bundle_data.elements]
        
        # 3. Bundle 레코드 생성
        bundles = create_bundle_records(
            bundle_data.group_id,
            bundle_data.name,
            bundle_data.description,
            bundle_data.release,
            elements,
            costs,
            price_ratios,
            db
        )
        
        # 3-1. 생성된 Bundle 검증
        if len(bundles) != len(elements):
            raise HTTPException(
                status_code=500, 
                detail=f"Bundle 생성 중 오류가 발생했습니다. 예상: {len(elements)}개, 실제: {len(bundles)}개"
            )
        
        # 3-2. Bundle ID 연속성 검증
        for i, bundle in enumerate(bundles, 1):
            if bundle.ID != i:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Bundle ID 연속성 오류. 예상: {i}, 실제: {bundle.ID}"
                )
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        # 5. 연쇄 업데이트는 불필요 (Bundle은 기존 Element 조합이므로)
        # Bundle 생성 시에는 상위 테이블 업데이트가 필요하지 않음
        
        # 6. 생성된 Bundle 조회하여 반환
        return await get_bundle(bundle_data.group_id, db)
        
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
        raise HTTPException(status_code=500, detail=f"Bundle 생성 중 오류가 발생했습니다: {str(e)}")

@bundles_router.put("/{group_id}")
async def update_bundle(group_id: int, bundle_data: BundleUpdateRequest, db: Session = Depends(get_db)):
    """Bundle 수정"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 기존 Bundle 조회
        existing_bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.GroupID == group_id,
            ProcedureBundle.Release == 1
        ).all()
        
        if not existing_bundles:
            raise HTTPException(status_code=404, detail="Bundle을 찾을 수 없습니다.")
        
        # 3. Group ID 변경 처리
        new_group_id = group_id
        if bundle_data.group_id is not None and bundle_data.group_id != group_id:
            # 새로운 Group ID 중복 확인
            existing_new_group = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == bundle_data.group_id,
                ProcedureBundle.Release == 1
            ).first()
            
            if existing_new_group:
                raise HTTPException(
                    status_code=400, 
                    detail=f"GroupID {bundle_data.group_id}는 이미 사용 중입니다."
                )
            
            new_group_id = bundle_data.group_id
        
        # 4. Bundle 정보 업데이트 (첫 번째 Bundle에만 적용)
        first_bundle = existing_bundles[0]
        if bundle_data.name is not None:
            first_bundle.Name = bundle_data.name
        if bundle_data.description is not None:
            first_bundle.Description = bundle_data.description
        if bundle_data.release is not None:
            first_bundle.Release = bundle_data.release
        
        # 5. Elements 업데이트 (제공된 경우)
        if bundle_data.elements is not None:
            # 5-1. Elements 검증 및 비용 계산
            elements = validate_bundle_elements(bundle_data.elements, db)
            costs = calculate_bundle_element_costs(elements, db)
            price_ratios = [elem.price_ratio for elem in bundle_data.elements]
            
            # 5-2. 기존 Elements 삭제
            for bundle in existing_bundles:
                db.delete(bundle)
            
            # 5-3. 새로운 Elements 생성 및 검증
            bundles = create_bundle_records(
                new_group_id,  # 새로운 Group ID 사용
                first_bundle.Name,
                first_bundle.Description,
                first_bundle.Release,
                elements,
                costs,
                price_ratios,
                db
            )
            
            # 5-4. 생성된 Bundle 검증
            if len(bundles) != len(elements):
                raise HTTPException(
                    status_code=500, 
                    detail=f"Bundle 생성 중 오류가 발생했습니다. 예상: {len(elements)}개, 실제: {len(bundles)}개"
                )
            
            # 5-5. Bundle ID 연속성 검증
            for i, bundle in enumerate(bundles, 1):
                if bundle.ID != i:
                    raise HTTPException(
                        status_code=500, 
                        detail=f"Bundle ID 연속성 오류. 예상: {i}, 실제: {bundle.ID}"
                    )
        
        # 6. Group ID 변경 시 참조 테이블 업데이트
        if new_group_id != group_id:
            try:
                cascade_update_bundle_group_id(group_id, new_group_id, db)
            except Exception as cascade_error:
                # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
                print(f"Bundle Group ID 변경 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        # 7. 트랜잭션 커밋
        db.commit()
        
        # 8. 연쇄 업데이트 실행 (별도 트랜잭션)
        try:
            cascade_update_by_bundle_group(new_group_id, db)  # 새로운 Group ID 사용
        except Exception as cascade_error:
            # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
            print(f"Bundle 수정 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        # 9. 수정된 Bundle 조회하여 반환
        return await get_bundle(new_group_id, db)  # 새로운 Group ID 사용
        
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
        raise HTTPException(status_code=500, detail=f"Bundle 수정 중 오류가 발생했습니다: {str(e)}")

@bundles_router.delete("/{group_id}")
async def delete_bundle(group_id: int, db: Session = Depends(get_db)):
    """Bundle 삭제"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 해당 GroupID의 모든 Bundle 조회
        bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.GroupID == group_id,
            ProcedureBundle.Release == 1
        ).all()
        
        if not bundles:
            raise HTTPException(status_code=404, detail="Bundle을 찾을 수 없습니다.")
        
        # 3. Sequence에서 참조 확인
        from db.models.procedure import ProcedureSequence
        sequence_count = db.query(ProcedureSequence).filter(
            ProcedureSequence.Bundle_ID == group_id,
            ProcedureSequence.Release == 1
        ).count()
        
        if sequence_count > 0:
            raise HTTPException(
                status_code=400, 
                detail=f"이 Bundle은 {sequence_count}개의 Sequence에서 사용 중입니다. 먼저 참조를 제거해주세요."
            )
        
        # 4. Product에서 참조 확인
        from db.models.product import ProductStandard, ProductEvent
        product_standard_count = db.query(ProductStandard).filter(
            ProductStandard.Bundle_ID == group_id,
            ProductStandard.Release == 1
        ).count()
        
        product_event_count = db.query(ProductEvent).filter(
            ProductEvent.Bundle_ID == group_id,
            ProductEvent.Release == 1
        ).count()
        
        if product_standard_count > 0 or product_event_count > 0:
            total_count = product_standard_count + product_event_count
            raise HTTPException(
                status_code=400, 
                detail=f"이 Bundle은 {total_count}개의 Product에서 사용 중입니다. 먼저 참조를 제거해주세요."
            )
        
        # 5. Bundle 삭제
        for bundle in bundles:
            db.delete(bundle)
        
        # 6. 트랜잭션 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": f"Bundle GroupID {group_id}가 성공적으로 삭제되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Bundle 삭제 중 오류가 발생했습니다: {str(e)}")

@bundles_router.put("/{group_id}/deactivate")
async def deactivate_bundle(group_id: int, db: Session = Depends(get_db)):
    """Bundle 비활성화"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. Bundle 조회
        bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.GroupID == group_id,
            ProcedureBundle.Release == 1
        ).all()
        
        if not bundles:
            raise HTTPException(status_code=404, detail="Bundle을 찾을 수 없습니다.")
        
        # 3. Bundle 비활성화
        for bundle in bundles:
            bundle.Release = 0
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": f"Bundle GroupID {group_id}가 비활성화되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Bundle 비활성화 중 오류가 발생했습니다: {str(e)}")

@bundles_router.put("/{group_id}/activate")
async def activate_bundle(group_id: int, db: Session = Depends(get_db)):
    """Bundle 활성화"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 비활성화된 Bundle 조회
        bundles = db.query(ProcedureBundle).filter(
            ProcedureBundle.GroupID == group_id,
            ProcedureBundle.Release == 0
        ).all()
        
        if not bundles:
            raise HTTPException(status_code=404, detail="비활성화된 Bundle을 찾을 수 없습니다.")
        
        # 3. Bundle 활성화
        for bundle in bundles:
            bundle.Release = 1
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        # 5. 연쇄 업데이트 실행 (별도 트랜잭션)
        try:
            cascade_update_by_bundle_group(group_id, db)
        except Exception as cascade_error:
            # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
            print(f"Bundle 활성화 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        return {
            "status": "success",
            "message": f"Bundle GroupID {group_id}가 활성화되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Bundle 활성화 중 오류가 발생했습니다: {str(e)}")
