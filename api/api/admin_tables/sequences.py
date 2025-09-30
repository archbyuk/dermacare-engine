"""
    Sequence CRUD API
    
    이 모듈은 Sequence의 생성, 조회, 수정, 삭제 기능을 제공합니다.
    GroupID 기반으로 시술 순서들을 관리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from pydantic import BaseModel, validator

from db.session import get_db
from db.models.procedure import ProcedureSequence, ProcedureElement, ProcedureBundle, ProcedureCustom
from db.models.consumables import Consumables
from .utils import calculate_element_procedure_cost, cascade_update_by_sequence_group

# 라우터 설정
sequences_router = APIRouter(
    prefix="/sequences",
    tags=["Sequences"]
)

# ============================================================================
# Pydantic 모델
# ============================================================================

class SequenceStepRequest(BaseModel):
    step_num: int
    name: Optional[str] = None  # 시퀀스 이름
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_interval: Optional[int] = None
    price_ratio: Optional[float] = 1.0  # NULL 허용, 기본값 1.0
    
    @validator('step_num')
    def validate_step_num(cls, v):
        if v <= 0:
            raise ValueError('Step Number는 0보다 커야 합니다.')
        return v
    
    @validator('element_id', 'bundle_id', 'custom_id')
    def validate_reference_ids(cls, v):
        if v is not None and v <= 0:
            raise ValueError('참조 ID는 0보다 커야 합니다.')
        return v
    
    @validator('price_ratio')
    def validate_price_ratio(cls, v):
        if v <= 0 or v > 1:
            raise ValueError('Price Ratio는 0과 1 사이의 값이어야 합니다.')
        return v
    
    @validator('sequence_interval')
    def validate_sequence_interval(cls, v):
        if v is not None and v < 0:
            raise ValueError('Sequence Interval는 0 이상이어야 합니다.')
        return v

class SequenceCreateRequest(BaseModel):
    group_id: int
    name: Optional[str] = None  # 시퀀스 이름
    release: int = 1  # 릴리즈 상태 (0 또는 1, 기본값 1)
    steps: List[SequenceStepRequest]
    
    @validator('group_id')
    def validate_group_id(cls, v):
        if v <= 0:
            raise ValueError('Group ID는 0보다 커야 합니다.')
        return v
    
    @validator('release')
    def validate_release(cls, v):
        if v not in [0, 1]:
            raise ValueError('Release는 0 또는 1이어야 합니다.')
        return v
    
    @validator('steps')
    def validate_steps(cls, v):
        if not v:
            raise ValueError('Sequence에는 최소 하나의 Step이 포함되어야 합니다.')
        if len(v) > 20:  # 최대 20개 Step 제한
            raise ValueError('Sequence에는 최대 20개의 Step만 포함할 수 있습니다.')
        
        # Step Number 중복 확인
        step_nums = [step.step_num for step in v]
        if len(step_nums) != len(set(step_nums)):
            raise ValueError('Step Number는 중복될 수 없습니다.')
        
        # 각 Step에서 참조 타입 검증
        for step in v:
            reference_count = sum([
                1 if step.element_id is not None else 0,
                1 if step.bundle_id is not None else 0,
                1 if step.custom_id is not None else 0
            ])
            if reference_count != 1:
                raise ValueError(f'Step {step.step_num}: Element, Bundle, Custom 중 정확히 하나만 선택해야 합니다.')
        
        return v

class SequenceUpdateRequest(BaseModel):
    steps: Optional[List[SequenceStepRequest]] = None
    
    @validator('steps')
    def validate_steps(cls, v):
        if v is not None:
            if not v:
                raise ValueError('Sequence에는 최소 하나의 Step이 포함되어야 합니다.')
            if len(v) > 20:
                raise ValueError('Sequence에는 최대 20개의 Step만 포함할 수 있습니다.')
            
            # Step Number 중복 확인
            step_nums = [step.step_num for step in v]
            if len(step_nums) != len(set(step_nums)):
                raise ValueError('Step Number는 중복될 수 없습니다.')
            
            # 각 Step에서 참조 타입 검증
            for step in v:
                reference_count = sum([
                    1 if step.element_id is not None else 0,
                    1 if step.bundle_id is not None else 0,
                    1 if step.custom_id is not None else 0
                ])
                if reference_count != 1:
                    raise ValueError(f'Step {step.step_num}: Element, Bundle, Custom 중 정확히 하나만 선택해야 합니다.')
        return v



class ConsumableInfo(BaseModel):
    id: int
    release: Optional[int] = None
    name: str
    description: Optional[str] = None
    unit_type: Optional[str] = None
    i_value: Optional[int] = None
    f_value: Optional[float] = None
    price: Optional[int] = None
    unit_price: Optional[int] = None
    vat: Optional[int] = None
    taxable_type: Optional[str] = None
    covered_type: Optional[str] = None

class ElementInfo(BaseModel):
    id: int
    release: Optional[int] = None
    name: str
    description: Optional[str] = None
    class_major: Optional[str] = None
    class_sub: Optional[str] = None
    class_detail: Optional[str] = None
    class_type: Optional[str] = None
    position_type: Optional[str] = None
    cost_time: Optional[float] = None
    plan_state: Optional[int] = None
    plan_count: Optional[int] = None
    plan_interval: Optional[int] = None
    consum_1_id: Optional[int] = None
    consum_1_count: Optional[int] = None
    procedure_level: Optional[str] = None
    procedure_cost: Optional[int] = None
    price: Optional[int] = None
    # 소모품 상세 정보 추가
    consumable_info: Optional[ConsumableInfo] = None

class BundleInfo(BaseModel):
    group_id: int
    id: Optional[int] = None
    release: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    element_id: Optional[int] = None
    element_cost: Optional[int] = None
    price_ratio: Optional[float] = None
    # Bundle에 포함된 Element들의 상세 정보
    elements: List[ElementInfo] = []

class CustomInfo(BaseModel):
    group_id: int
    id: Optional[int] = None
    release: Optional[int] = None
    name: str
    description: Optional[str] = None
    element_id: Optional[int] = None
    custom_count: Optional[int] = None
    element_limit: Optional[int] = None
    element_cost: Optional[int] = None
    price_ratio: Optional[float] = None
    # Custom에 포함된 Element들의 상세 정보
    elements: List[ElementInfo] = []

# POST API용 간단한 응답 모델
class SequenceStepCreateResponse(BaseModel):
    id: int
    group_id: int
    name: Optional[str] = None
    step_num: int
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_interval: Optional[int] = None
    procedure_cost: Optional[int] = None
    price_ratio: Optional[float] = None
    release: int = 1

class SequenceCreateResponse(BaseModel):
    group_id: int
    name: Optional[str] = None
    release: int = 1
    steps: List[SequenceStepCreateResponse] = []

# GET API용 상세 응답 모델
class SequenceStepDetailResponse(BaseModel):
    id: int
    group_id: int
    name: Optional[str] = None
    step_num: int
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_interval: Optional[int] = None
    procedure_cost: Optional[int] = None
    price_ratio: Optional[float] = None
    release: int = 1
    
    # 참조 객체 상세 정보
    element_info: Optional[ElementInfo] = None
    bundle_info: Optional[BundleInfo] = None
    custom_info: Optional[CustomInfo] = None

class SequenceResponse(BaseModel):
    group_id: int
    steps: List[SequenceStepDetailResponse] = []

    class Config:
        from_attributes = True

# ============================================================================
# 트랜잭션 헬퍼 함수들
# ============================================================================

def validate_sequence_steps(steps: List[SequenceStepRequest], db: Session) -> List[dict]:
    """
    Sequence Steps의 유효성을 검증하고 참조 객체들을 반환합니다.
    
    Args:
        steps: 검증할 Step 요청 리스트
        db: 데이터베이스 세션
    
    Returns:
        List[dict]: 검증된 참조 정보 리스트
    
    Raises:
        HTTPException: 검증 실패 시
    """
    validated_steps = []
    
    for step_data in steps:
        step_info = {
            'step_num': step_data.step_num,
            'name': step_data.name,  # 시퀀스 이름 추가
            'sequence_interval': step_data.sequence_interval,
            'price_ratio': step_data.price_ratio,
            'reference_type': None,
            'reference_id': None,
            'procedure_cost': 0
        }
        
        # Element 참조 확인
        if step_data.element_id is not None:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == step_data.element_id,
                ProcedureElement.Release == 1
            ).first()
            
            if not element:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Element ID {step_data.element_id}를 찾을 수 없습니다."
                )
            
            step_info['reference_type'] = 'element'
            step_info['reference_id'] = step_data.element_id
            step_info['procedure_cost'] = element.Procedure_Cost
        
        # Bundle 참조 확인
        elif step_data.bundle_id is not None:
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == step_data.bundle_id,
                ProcedureBundle.Release == 1
            ).all()
            
            if not bundles:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Bundle GroupID {step_data.bundle_id}를 찾을 수 없습니다."
                )
            
            step_info['reference_type'] = 'bundle'
            step_info['reference_id'] = step_data.bundle_id
            step_info['procedure_cost'] = sum(bundle.Element_Cost for bundle in bundles)
        
        # Custom 참조 확인
        elif step_data.custom_id is not None:
            customs = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == step_data.custom_id,
                ProcedureCustom.Release == 1
            ).all()
            
            if not customs:
                raise HTTPException(
                    status_code=404, 
                    detail=f"Custom GroupID {step_data.custom_id}를 찾을 수 없습니다."
                )
            
            step_info['reference_type'] = 'custom'
            step_info['reference_id'] = step_data.custom_id
            step_info['procedure_cost'] = sum(custom.Element_Cost for custom in customs)
        
        validated_steps.append(step_info)
    
    return validated_steps

def create_sequence_records(
    group_id: int,
    name: Optional[str],
    release: int,
    steps: List[dict],
    db: Session
) -> List[ProcedureSequence]:
    """
    Sequence 레코드들을 생성합니다.
    
    Args:
        group_id: Sequence Group ID
        name: 시퀀스 이름
        release: 릴리즈 상태 (0 또는 1)
        steps: 검증된 Step 정보 리스트
        db: 데이터베이스 세션
    
    Returns:
        List[ProcedureSequence]: 생성된 Sequence 객체 리스트
    """
    sequences = []
    
    for i, step_info in enumerate(steps, 1):
        sequence = ProcedureSequence(
            GroupID=group_id,
            ID=i,
            Release=release,
            Name=name,  # 시퀀스 이름 사용
            Step_Num=step_info['step_num'],
            Element_ID=step_info['reference_id'] if step_info['reference_type'] == 'element' else None,
            Bundle_ID=step_info['reference_id'] if step_info['reference_type'] == 'bundle' else None,
            Custom_ID=step_info['reference_id'] if step_info['reference_type'] == 'custom' else None,
            Sequence_Interval=step_info['sequence_interval'],
            Procedure_Cost=step_info['procedure_cost'],
            Price_Ratio=step_info['price_ratio'],
        )
        
        db.add(sequence)
        sequences.append(sequence)
    
    return sequences

# ============================================================================
# API 엔드포인트
# ============================================================================

@sequences_router.get("/")
async def get_sequences_list(db: Session = Depends(get_db)):
    """Sequence 목록 조회 (GroupID별로 그룹화) - 상세 정보 포함"""
    try:
        # N+1 쿼리 문제 해결: LEFT JOIN을 사용하여 한 번의 쿼리로 모든 데이터 조회
        sequences_with_details = db.query(
            ProcedureSequence,
            ProcedureElement,
            Consumables
        ).outerjoin(
            ProcedureElement,
            ProcedureElement.ID == ProcedureSequence.Element_ID
        ).outerjoin(
            Consumables,
            and_(
                Consumables.ID == ProcedureElement.Consum_1_ID,
                Consumables.Release == 1
            )
        ).order_by(ProcedureSequence.GroupID, ProcedureSequence.Step_Num).all()
        
        # GroupID별로 그룹화
        sequence_groups = {}
        for sequence, element, consumable in sequences_with_details:
            if sequence.GroupID not in sequence_groups:
                sequence_groups[sequence.GroupID] = {
                    'group_id': sequence.GroupID,
                    'sequence_name': sequence.Name,
                    'procedure_cost': sequence.Procedure_Cost,
                    'steps': []
                }
            
            # 각 시퀀스 스텝의 상세 정보를 포함하여 생성
            step_detail = SequenceStepDetailResponse(
                id=sequence.ID,
                group_id=sequence.GroupID,
                name=sequence.Name,
                step_num=sequence.Step_Num,
                element_id=sequence.Element_ID,
                bundle_id=sequence.Bundle_ID,
                custom_id=sequence.Custom_ID,
                sequence_interval=sequence.Sequence_Interval,
                procedure_cost=sequence.Procedure_Cost,
                price_ratio=sequence.Price_Ratio,
                release=sequence.Release
            )
            
            # Element 정보 조회
            if sequence.Element_ID:
                element = db.query(ProcedureElement).filter(
                    ProcedureElement.ID == sequence.Element_ID
                ).first()
                if element:
                    # 소모품 정보 조회
                    consumable_info = None
                    if element.Consum_1_ID:
                        consumable = db.query(Consumables).filter(
                            Consumables.ID == element.Consum_1_ID
                        ).first()
                        if consumable:
                            consumable_info = ConsumableInfo(
                                id=consumable.ID,
                                release=consumable.Release,
                                name=consumable.Name,
                                description=consumable.Description,
                                unit_type=consumable.Unit_Type,
                                i_value=consumable.I_Value,
                                f_value=consumable.F_Value,
                                price=consumable.Price,
                                unit_price=consumable.Unit_Price,
                                vat=consumable.VAT,
                                taxable_type=consumable.Taxable_Type,
                                covered_type=consumable.Covered_Type
                            )
                    
                    step_detail.element_info = ElementInfo(
                        id=element.ID,
                        release=element.Release,
                        name=element.Name,
                        description=element.description,
                        class_major=element.Class_Major,
                        class_sub=element.Class_Sub,
                        class_detail=element.Class_Detail,
                        class_type=element.Class_Type,
                        position_type=element.Position_Type,
                        cost_time=element.Cost_Time,
                        plan_state=element.Plan_State,
                        plan_count=element.Plan_Count,
                        plan_interval=element.Plan_Interval,
                        consum_1_id=element.Consum_1_ID,
                        consum_1_count=element.Consum_1_Count,
                        procedure_level=element.Procedure_Level,
                        procedure_cost=element.Procedure_Cost,
                        price=element.Price,
                        consumable_info=consumable_info
                    )
            
            # Bundle 정보 조회
            elif sequence.Bundle_ID:
                bundle = db.query(ProcedureBundle).filter(
                    ProcedureBundle.GroupID == sequence.Bundle_ID
                ).first()
                if bundle:
                    # Bundle에 포함된 모든 Element 조회
                    bundle_elements = db.query(ProcedureElement).join(
                        ProcedureBundle, 
                        ProcedureElement.ID == ProcedureBundle.Element_ID
                    ).filter(
                        ProcedureBundle.GroupID == sequence.Bundle_ID
                    ).all()
                    
                    # Element 상세 정보 리스트 생성
                    element_infos = []
                    for element in bundle_elements:
                        # 소모품 정보 조회
                        consumable_info = None
                        if element.Consum_1_ID:
                            consumable = db.query(Consumables).filter(
                                Consumables.ID == element.Consum_1_ID
                            ).first()
                            if consumable:
                                consumable_info = ConsumableInfo(
                                    id=consumable.ID,
                                    release=consumable.Release,
                                    name=consumable.Name,
                                    description=consumable.Description,
                                    unit_type=consumable.Unit_Type,
                                    i_value=consumable.I_Value,
                                    f_value=consumable.F_Value,
                                    price=consumable.Price,
                                    unit_price=consumable.Unit_Price,
                                    vat=consumable.VAT,
                                    taxable_type=consumable.Taxable_Type,
                                    covered_type=consumable.Covered_Type
                                )
                        
                        element_infos.append(ElementInfo(
                            id=element.ID,
                            release=element.Release,
                            name=element.Name,
                            description=element.description,
                            class_major=element.Class_Major,
                            class_sub=element.Class_Sub,
                            class_detail=element.Class_Detail,
                            class_type=element.Class_Type,
                            position_type=element.Position_Type,
                            cost_time=element.Cost_Time,
                            plan_state=element.Plan_State,
                            plan_count=element.Plan_Count,
                            plan_interval=element.Plan_Interval,
                            consum_1_id=element.Consum_1_ID,
                            consum_1_count=element.Consum_1_Count,
                            procedure_level=element.Procedure_Level,
                            procedure_cost=element.Procedure_Cost,
                            price=element.Price,
                            consumable_info=consumable_info
                        ))
                    
                    step_detail.bundle_info = BundleInfo(
                        group_id=bundle.GroupID,
                        name=bundle.Name,
                        description=bundle.Description,
                        element_cost=bundle.Element_Cost,
                        price_ratio=bundle.Price_Ratio,
                        elements=element_infos
                    )
            
            # Custom 정보 조회
            elif sequence.Custom_ID:
                custom = db.query(ProcedureCustom).filter(
                    ProcedureCustom.GroupID == sequence.Custom_ID
                ).first()
                if custom:
                    # Custom에 포함된 Element 조회 (Custom은 하나의 Element만 참조)
                    element = None
                    if custom.Element_ID:
                        element = db.query(ProcedureElement).filter(
                            ProcedureElement.ID == custom.Element_ID
                        ).first()
                    
                    # Element 상세 정보 생성
                    element_info = None
                    if element:
                        # 소모품 정보 조회
                        consumable_info = None
                        if element.Consum_1_ID:
                            consumable = db.query(Consumables).filter(
                                Consumables.ID == element.Consum_1_ID
                            ).first()
                            if consumable:
                                consumable_info = ConsumableInfo(
                                    id=consumable.ID,
                                    release=consumable.Release,
                                    name=consumable.Name,
                                    description=consumable.Description,
                                    unit_type=consumable.Unit_Type,
                                    i_value=consumable.I_Value,
                                    f_value=consumable.F_Value,
                                    price=consumable.Price,
                                    unit_price=consumable.Unit_Price,
                                    vat=consumable.VAT,
                                    taxable_type=consumable.Taxable_Type,
                                    covered_type=consumable.Covered_Type
                                )
                        
                        element_info = ElementInfo(
                            id=element.ID,
                            release=element.Release,
                            name=element.Name,
                            description=element.description,
                            class_major=element.Class_Major,
                            class_sub=element.Class_Sub,
                            class_detail=element.Class_Detail,
                            class_type=element.Class_Type,
                            position_type=element.Position_Type,
                            cost_time=element.Cost_Time,
                            plan_state=element.Plan_State,
                            plan_count=element.Plan_Count,
                            plan_interval=element.Plan_Interval,
                            consum_1_id=element.Consum_1_ID,
                            consum_1_count=element.Consum_1_Count,
                            procedure_level=element.Procedure_Level,
                            procedure_cost=element.Procedure_Cost,
                            price=element.Price,
                            consumable_info=consumable_info
                        )
                    
                    step_detail.custom_info = CustomInfo(
                        group_id=custom.GroupID,
                        name=custom.Name,
                        description=custom.Description,
                        custom_count=custom.Custom_Count,
                        element_limit=custom.Element_Limit,
                        element_cost=custom.Element_Cost,
                        price_ratio=custom.Price_Ratio,
                        elements=[element_info] if element_info else []
                    )
            
            sequence_groups[sequence.GroupID]['steps'].append(step_detail)
        
        return list(sequence_groups.values())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sequence 목록 조회 중 오류가 발생했습니다: {str(e)}")

@sequences_router.get("/{group_id}")
async def get_sequence(group_id: int, db: Session = Depends(get_db)):
    """특정 Sequence 조회 (GroupID 기준) - 상세 정보 포함"""
    try:
        # Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 해당 GroupID의 모든 Sequence 조회 (Release 상태와 관계없이)
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == group_id
        ).order_by(ProcedureSequence.Step_Num).all()
        
        if not sequences:
            raise HTTPException(status_code=404, detail="Sequence를 찾을 수 없습니다.")
        
        # 각 시퀀스 스텝의 상세 정보를 포함하여 응답 생성
        detailed_steps = []
        for sequence in sequences:
            step_detail = SequenceStepDetailResponse(
                id=sequence.ID,
                group_id=sequence.GroupID,
                name=sequence.Name,
                step_num=sequence.Step_Num,
                element_id=sequence.Element_ID,
                bundle_id=sequence.Bundle_ID,
                custom_id=sequence.Custom_ID,
                sequence_interval=sequence.Sequence_Interval,
                procedure_cost=sequence.Procedure_Cost,
                price_ratio=sequence.Price_Ratio,
                release=sequence.Release
            )
            
            # Element 정보 조회 (상세 정보 포함)
            if sequence.Element_ID:
                element = db.query(ProcedureElement).filter(
                    ProcedureElement.ID == sequence.Element_ID
                ).first()
                
                # Element 정보 조회
                if element:
                    # 소모품 정보 조회
                    consumable_info = None
                    if element.Consum_1_ID:
                        consumable = db.query(Consumables).filter(
                            Consumables.ID == element.Consum_1_ID
                        ).first()
                        if consumable:
                            consumable_info = ConsumableInfo(
                                id=consumable.ID,
                                release=consumable.Release,
                                name=consumable.Name,
                                description=consumable.Description,
                                unit_type=consumable.Unit_Type,
                                i_value=consumable.I_Value,
                                f_value=consumable.F_Value,
                                price=consumable.Price,
                                unit_price=consumable.Unit_Price,
                                vat=consumable.VAT,
                                taxable_type=consumable.Taxable_Type,
                                covered_type=consumable.Covered_Type
                            )
                    
                    step_detail.element_info = ElementInfo(
                        id=element.ID,
                        release=element.Release,
                        name=element.Name,
                        description=element.description,
                        class_major=element.Class_Major,
                        class_sub=element.Class_Sub,
                        class_detail=element.Class_Detail,
                        class_type=element.Class_Type,
                        position_type=element.Position_Type,
                        cost_time=element.Cost_Time,
                        plan_state=element.Plan_State,
                        plan_count=element.Plan_Count,
                        plan_interval=element.Plan_Interval,
                        consum_1_id=element.Consum_1_ID,
                        consum_1_count=element.Consum_1_Count,
                        procedure_level=element.Procedure_Level,
                        procedure_cost=element.Procedure_Cost,
                        price=element.Price,
                        consumable_info=consumable_info
                    )
            
            # Bundle 정보 조회
            elif sequence.Bundle_ID:
                bundle = db.query(ProcedureBundle).filter(
                    ProcedureBundle.GroupID == sequence.Bundle_ID
                ).first()
                if bundle:
                    # Bundle에 포함된 모든 Element 조회
                    bundle_elements = db.query(ProcedureElement).join(
                        ProcedureBundle, 
                        ProcedureElement.ID == ProcedureBundle.Element_ID
                    ).filter(
                        ProcedureBundle.GroupID == sequence.Bundle_ID
                    ).all()
                    
                    # Element 상세 정보 리스트 생성
                    element_infos = []
                    for element in bundle_elements:
                        # 소모품 정보 조회
                        consumable_info = None
                        if element.Consum_1_ID:
                            consumable = db.query(Consumables).filter(
                                Consumables.ID == element.Consum_1_ID
                            ).first()
                            if consumable:
                                consumable_info = ConsumableInfo(
                                    id=consumable.ID,
                                    release=consumable.Release,
                                    name=consumable.Name,
                                    description=consumable.Description,
                                    unit_type=consumable.Unit_Type,
                                    i_value=consumable.I_Value,
                                    f_value=consumable.F_Value,
                                    price=consumable.Price,
                                    unit_price=consumable.Unit_Price,
                                    vat=consumable.VAT,
                                    taxable_type=consumable.Taxable_Type,
                                    covered_type=consumable.Covered_Type
                                )
                        
                        element_infos.append(ElementInfo(
                            id=element.ID,
                            release=element.Release,
                            name=element.Name,
                            description=element.description,
                            class_major=element.Class_Major,
                            class_sub=element.Class_Sub,
                            class_detail=element.Class_Detail,
                            class_type=element.Class_Type,
                            position_type=element.Position_Type,
                            cost_time=element.Cost_Time,
                            plan_state=element.Plan_State,
                            plan_count=element.Plan_Count,
                            plan_interval=element.Plan_Interval,
                            consum_1_id=element.Consum_1_ID,
                            consum_1_count=element.Consum_1_Count,
                            procedure_level=element.Procedure_Level,
                            procedure_cost=element.Procedure_Cost,
                            price=element.Price,
                            consumable_info=consumable_info
                        ))
                    
                    step_detail.bundle_info = BundleInfo(
                        group_id=bundle.GroupID,
                        name=bundle.Name,
                        description=bundle.Description,
                        element_cost=bundle.Element_Cost,
                        price_ratio=bundle.Price_Ratio,
                        elements=element_infos
                    )
            
            # Custom 정보 조회
            elif sequence.Custom_ID:
                custom = db.query(ProcedureCustom).filter(
                    ProcedureCustom.GroupID == sequence.Custom_ID
                ).first()
                if custom:
                    # Custom에 포함된 Element 조회 (Custom은 하나의 Element만 참조)
                    element = None
                    if custom.Element_ID:
                        element = db.query(ProcedureElement).filter(
                            ProcedureElement.ID == custom.Element_ID
                        ).first()
                    
                    # Element 상세 정보 생성
                    element_info = None
                    if element:
                        # 소모품 정보 조회
                        consumable_info = None
                        if element.Consum_1_ID:
                            consumable = db.query(Consumables).filter(
                                Consumables.ID == element.Consum_1_ID
                            ).first()
                            if consumable:
                                consumable_info = ConsumableInfo(
                                    id=consumable.ID,
                                    release=consumable.Release,
                                    name=consumable.Name,
                                    description=consumable.Description,
                                    unit_type=consumable.Unit_Type,
                                    i_value=consumable.I_Value,
                                    f_value=consumable.F_Value,
                                    price=consumable.Price,
                                    unit_price=consumable.Unit_Price,
                                    vat=consumable.VAT,
                                    taxable_type=consumable.Taxable_Type,
                                    covered_type=consumable.Covered_Type
                                )
                        
                        element_info = ElementInfo(
                            id=element.ID,
                            release=element.Release,
                            name=element.Name,
                            description=element.description,
                            class_major=element.Class_Major,
                            class_sub=element.Class_Sub,
                            class_detail=element.Class_Detail,
                            class_type=element.Class_Type,
                            position_type=element.Position_Type,
                            cost_time=element.Cost_Time,
                            plan_state=element.Plan_State,
                            plan_count=element.Plan_Count,
                            plan_interval=element.Plan_Interval,
                            consum_1_id=element.Consum_1_ID,
                            consum_1_count=element.Consum_1_Count,
                            procedure_level=element.Procedure_Level,
                            procedure_cost=element.Procedure_Cost,
                            price=element.Price,
                            consumable_info=consumable_info
                        )
                    step_detail.custom_info = CustomInfo(
                        group_id=custom.GroupID,
                        name=custom.Name,
                        description=custom.Description,
                        custom_count=custom.Custom_Count,
                        element_limit=custom.Element_Limit,
                        element_cost=custom.Element_Cost,
                        price_ratio=custom.Price_Ratio,
                        elements=[element_info] if element_info else []
                    )
            
            detailed_steps.append(step_detail)
        
        sequence_response = SequenceResponse(
            group_id=group_id,
            steps=detailed_steps
        )
        
        return sequence_response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sequence 조회 중 오류가 발생했습니다: {str(e)}")

@sequences_router.post("/")
async def create_sequence(sequence_data: SequenceCreateRequest, db: Session = Depends(get_db)):
    """Sequence 생성"""
    try:
        # 1. GroupID 중복 확인 (같은 릴리즈 상태인 경우만)
        existing_sequence = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == sequence_data.group_id,
            ProcedureSequence.Release == sequence_data.release
        ).first()
        
        if existing_sequence:
            raise HTTPException(
                status_code=400, 
                detail=f"GroupID {sequence_data.group_id}와 Release {sequence_data.release}는 이미 사용 중입니다."
            )
        
        # 2. Steps 검증 및 비용 계산
        steps = validate_sequence_steps(sequence_data.steps, db)
        
        # 3. Sequence 레코드 생성
        sequences = create_sequence_records(
            sequence_data.group_id,
            sequence_data.name,
            sequence_data.release,
            steps,
            db
        )
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        # 5. 연쇄 업데이트는 불필요 (시퀀스는 기존 데이터 조합이므로)
        # 시퀀스 생성 시에는 상위 테이블 업데이트가 필요하지 않음
        
        # 6. 생성된 Sequence 객체들을 다시 조회하여 간단한 응답으로 변환
        try:
            created_sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == sequence_data.group_id
            ).order_by(ProcedureSequence.Step_Num).all()
            
            created_steps = []
            for seq in created_sequences:
                step_response = SequenceStepCreateResponse(
                    id=seq.ID,
                    group_id=seq.GroupID,
                    name=seq.Name,
                    step_num=seq.Step_Num,
                    element_id=seq.Element_ID,
                    bundle_id=seq.Bundle_ID,
                    custom_id=seq.Custom_ID,
                    sequence_interval=seq.Sequence_Interval,
                    procedure_cost=seq.Procedure_Cost,
                    price_ratio=seq.Price_Ratio,
                    release=seq.Release
                )
                created_steps.append(step_response)
            
            sequence_response = SequenceCreateResponse(
                group_id=sequence_data.group_id,
                name=sequence_data.name,
                release=sequence_data.release,
                steps=created_steps
            )
            
            # 시퀀스 생성이 성공했으므로 성공 응답 반환
            return sequence_response
            
        except Exception as response_error:
            # 응답 생성 중 오류가 발생해도 시퀀스는 이미 생성되었으므로 간단한 성공 응답 반환
            print(f"응답 생성 중 오류: {str(response_error)}")
            print(f"오류 타입: {type(response_error)}")
            import traceback
            print(f"스택 트레이스: {traceback.format_exc()}")
            return {
                "group_id": sequence_data.group_id,
                "name": sequence_data.name,
                "release": sequence_data.release,
                "steps": [],
                "message": "시퀀스가 성공적으로 생성되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Sequence 생성 중 오류가 발생했습니다: {str(e)}")

@sequences_router.put("/{group_id}")
async def update_sequence(group_id: int, sequence_data: SequenceUpdateRequest, db: Session = Depends(get_db)):
    """Sequence 수정"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 기존 Sequence 조회
        existing_sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == group_id,
            ProcedureSequence.Release == 1
        ).all()
        
        if not existing_sequences:
            raise HTTPException(status_code=404, detail="Sequence를 찾을 수 없습니다.")
        
        # 3. Steps 업데이트 (제공된 경우)
        sequences = None
        if sequence_data.steps is not None:
            # 3-1. Steps 검증 및 비용 계산
            steps = validate_sequence_steps(sequence_data.steps, db)
            
            # 3-2. 기존 Steps 삭제
            for sequence in existing_sequences:
                db.delete(sequence)
            
            # 3-3. 새로운 Steps 생성
            sequences = create_sequence_records(
                group_id,
                steps,
                db
            )
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        # 5. 연쇄 업데이트 실행 (시퀀스 수정 시에는 필요 - Product 마진 재계산)
        try:
            cascade_update_by_sequence_group(group_id, db)
        except Exception as cascade_error:
            # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
            print(f"Sequence 수정 후 연쇄 업데이트 실패: {str(cascade_error)}")
            # 연쇄 업데이트 실패는 시퀀스 수정 실패로 처리하지 않음
        
        # 6. 수정된 Sequence 조회하여 반환
        if sequences:
            # 새로 생성된 객체들을 상세 정보와 함께 응답으로 변환
            detailed_steps = []
            for seq in sequences:
                step_detail = SequenceStepDetailResponse(
                    id=seq.ID,
                    group_id=seq.GroupID,
                    name=seq.Name,
                    step_num=seq.Step_Num,
                    element_id=seq.Element_ID,
                    bundle_id=seq.Bundle_ID,
                    custom_id=seq.Custom_ID,
                    sequence_interval=seq.Sequence_Interval,
                    procedure_cost=seq.Procedure_Cost,
                    price_ratio=seq.Price_Ratio,
                    release=seq.Release
                )
                
                # 참조 객체 상세 정보 조회
                if seq.Element_ID:
                    element = db.query(ProcedureElement).filter(
                        ProcedureElement.ID == seq.Element_ID
                    ).first()
                    if element:
                        # 소모품 정보 조회
                        consumable_info = None
                        if element.Consum_1_ID:
                            consumable = db.query(Consumables).filter(
                                Consumables.ID == element.Consum_1_ID
                            ).first()
                            if consumable:
                                consumable_info = ConsumableInfo(
                                    id=consumable.ID,
                                    release=consumable.Release,
                                    name=consumable.Name,
                                    description=consumable.Description,
                                    unit_type=consumable.Unit_Type,
                                    i_value=consumable.I_Value,
                                    f_value=consumable.F_Value,
                                    price=consumable.Price,
                                    unit_price=consumable.Unit_Price,
                                    vat=consumable.VAT,
                                    taxable_type=consumable.Taxable_Type,
                                    covered_type=consumable.Covered_Type
                                )
                        
                        step_detail.element_info = ElementInfo(
                            id=element.ID,
                            name=element.Name,
                            description=element.description,
                            class_major=element.Class_Major,
                            class_sub=element.Class_Sub,
                            class_detail=element.Class_Detail,
                            class_type=element.Class_Type,
                            procedure_cost=element.Procedure_Cost,
                            price=element.Price,
                            consumable_info=consumable_info
                        )
                elif seq.Bundle_ID:
                    bundle = db.query(ProcedureBundle).filter(
                        ProcedureBundle.GroupID == seq.Bundle_ID
                    ).first()
                    if bundle:
                        # Bundle에 포함된 모든 Element 조회
                        bundle_elements = db.query(ProcedureElement).join(
                            ProcedureBundle, 
                            ProcedureElement.ID == ProcedureBundle.Element_ID
                        ).filter(
                            ProcedureBundle.GroupID == seq.Bundle_ID
                        ).all()
                        
                        # Element 상세 정보 리스트 생성
                        element_infos = []
                        for element in bundle_elements:
                            # 소모품 정보 조회
                            consumable_info = None
                            if element.Consum_1_ID:
                                consumable = db.query(Consumables).filter(
                                    Consumables.ID == element.Consum_1_ID
                                ).first()
                                if consumable:
                                    consumable_info = ConsumableInfo(
                                        id=consumable.ID,
                                        release=consumable.Release,
                                        name=consumable.Name,
                                        description=consumable.Description,
                                        unit_type=consumable.Unit_Type,
                                        i_value=consumable.I_Value,
                                        f_value=consumable.F_Value,
                                        price=consumable.Price,
                                        unit_price=consumable.Unit_Price,
                                        vat=consumable.VAT,
                                        taxable_type=consumable.Taxable_Type,
                                        covered_type=consumable.Covered_Type
                                    )
                            
                            element_infos.append(ElementInfo(
                                id=element.ID,
                                name=element.Name,
                                description=element.description,
                                class_major=element.Class_Major,
                                class_sub=element.Class_Sub,
                                class_detail=element.Class_Detail,
                                class_type=element.Class_Type,
                                procedure_cost=element.Procedure_Cost,
                                price=element.Price,
                                consumable_info=consumable_info
                            ))
                        
                        step_detail.bundle_info = BundleInfo(
                            group_id=bundle.GroupID,
                            name=bundle.Name,
                            description=bundle.Description,
                            element_cost=bundle.Element_Cost,
                            price_ratio=bundle.Price_Ratio,
                            elements=element_infos
                        )
                elif seq.Custom_ID:
                    custom = db.query(ProcedureCustom).filter(
                        ProcedureCustom.GroupID == seq.Custom_ID
                    ).first()
                    if custom:
                        # Custom에 포함된 Element 조회 (Custom은 하나의 Element만 참조)
                        element = None
                        if custom.Element_ID:
                            element = db.query(ProcedureElement).filter(
                                ProcedureElement.ID == custom.Element_ID
                            ).first()
                        
                        # Element 상세 정보 생성
                        element_info = None
                        if element:
                            # 소모품 정보 조회
                            consumable_info = None
                            if element.Consum_1_ID:
                                consumable = db.query(Consumables).filter(
                                    Consumables.ID == element.Consum_1_ID
                                ).first()
                                if consumable:
                                    consumable_info = ConsumableInfo(
                                        id=consumable.ID,
                                        release=consumable.Release,
                                        name=consumable.Name,
                                        description=consumable.Description,
                                        unit_type=consumable.Unit_Type,
                                        i_value=consumable.I_Value,
                                        f_value=consumable.F_Value,
                                        price=consumable.Price,
                                        unit_price=consumable.Unit_Price,
                                        vat=consumable.VAT,
                                        taxable_type=consumable.Taxable_Type,
                                        covered_type=consumable.Covered_Type
                                    )
                            
                            element_info = ElementInfo(
                                id=element.ID,
                                name=element.Name,
                                description=element.description,
                                class_major=element.Class_Major,
                                class_sub=element.Class_Sub,
                                class_detail=element.Class_Detail,
                                class_type=element.Class_Type,
                                procedure_cost=element.Procedure_Cost,
                                price=element.Price,
                                consumable_info=consumable_info
                            )
                        
                        step_detail.custom_info = CustomInfo(
                            group_id=custom.GroupID,
                            name=custom.Name,
                            description=custom.Description,
                            custom_count=custom.Custom_Count,
                            element_limit=custom.Element_Limit,
                            element_cost=custom.Element_Cost,
                            price_ratio=custom.Price_Ratio,
                            elements=[element_info] if element_info else []
                        )
                
                detailed_steps.append(step_detail)
            
            sequence_response = SequenceResponse(
                group_id=group_id,
                steps=detailed_steps
            )
            return sequence_response
        else:
            # Steps가 수정되지 않은 경우 기존 데이터 조회
            return await get_sequence(group_id, db)
        
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
        raise HTTPException(status_code=500, detail=f"Sequence 수정 중 오류가 발생했습니다: {str(e)}")

@sequences_router.delete("/{group_id}")
async def delete_sequence(group_id: int, db: Session = Depends(get_db)):
    """Sequence 삭제"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 해당 GroupID의 모든 Sequence 조회
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == group_id,
            ProcedureSequence.Release == 1
        ).all()
        
        if not sequences:
            raise HTTPException(status_code=404, detail="Sequence를 찾을 수 없습니다.")
        
        # 3. Product에서 참조 확인
        from db.models.product import ProductStandard, ProductEvent
        product_standard_count = db.query(ProductStandard).filter(
            ProductStandard.Sequence_ID == group_id,
            ProductStandard.Release == 1
        ).count()
        
        product_event_count = db.query(ProductEvent).filter(
            ProductEvent.Sequence_ID == group_id,
            ProductEvent.Release == 1
        ).count()
        
        if product_standard_count > 0 or product_event_count > 0:
            total_count = product_standard_count + product_event_count
            raise HTTPException(
                status_code=400, 
                detail=f"이 Sequence는 {total_count}개의 Product에서 사용 중입니다. 먼저 참조를 제거해주세요."
            )
        
        # 4. Sequence 삭제
        for sequence in sequences:
            db.delete(sequence)
        
        # 5. 트랜잭션 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": f"Sequence GroupID {group_id}가 성공적으로 삭제되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Sequence 삭제 중 오류가 발생했습니다: {str(e)}")

@sequences_router.put("/{group_id}/deactivate")
async def deactivate_sequence(group_id: int, db: Session = Depends(get_db)):
    """Sequence 비활성화"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. Sequence 조회
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == group_id,
            ProcedureSequence.Release == 1
        ).all()
        
        if not sequences:
            raise HTTPException(status_code=404, detail="Sequence를 찾을 수 없습니다.")
        
        # 3. Sequence 비활성화
        for sequence in sequences:
            sequence.Release = 0
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        return {
            "status": "success",
            "message": f"Sequence GroupID {group_id}가 비활성화되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Sequence 비활성화 중 오류가 발생했습니다: {str(e)}")

@sequences_router.put("/{group_id}/activate")
async def activate_sequence(group_id: int, db: Session = Depends(get_db)):
    """Sequence 활성화"""
    try:
        # 1. Group ID 검증
        if group_id <= 0:
            raise HTTPException(status_code=400, detail="Group ID는 0보다 커야 합니다.")
        
        # 2. 비활성화된 Sequence 조회
        sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == group_id,
            ProcedureSequence.Release == 0
        ).all()
        
        if not sequences:
            raise HTTPException(status_code=404, detail="비활성화된 Sequence를 찾을 수 없습니다.")
        
        # 3. Sequence 활성화
        for sequence in sequences:
            sequence.Release = 1
        
        # 4. 트랜잭션 커밋
        db.commit()
        
        # 5. 연쇄 업데이트 실행 (별도 트랜잭션)
        try:
            cascade_update_by_sequence_group(group_id, db)
        except Exception as cascade_error:
            # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
            print(f"Sequence 활성화 후 연쇄 업데이트 실패: {str(cascade_error)}")
            # 연쇄 업데이트 실패는 시퀀스 활성화 실패로 처리하지 않음
        
        return {
            "status": "success",
            "message": f"Sequence GroupID {group_id}가 활성화되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Sequence 활성화 중 오류가 발생했습니다: {str(e)}")
