"""
    Membership CRUD API
    
    이 모듈은 Membership의 생성, 조회, 수정, 삭제 기능을 제공합니다.
    멤버십 상품들을 관리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from typing import Optional, List
from pydantic import BaseModel, validator
from datetime import datetime

from db.session import get_db
from db.models.membership import Membership
from db.models.info import InfoMembership
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence
from .utils import cascade_update_membership_id

# 라우터 설정
membership_router = APIRouter(
    prefix="/membership",
    tags=["Membership"]
)

# ============================================================================
# Pydantic 모델
# ============================================================================

class InfoMembershipUpdateRequest(BaseModel):
    id: int  # Info ID 필수
    membership_name: Optional[str] = None
    membership_description: Optional[str] = None
    precautions: Optional[str] = None
    release: Optional[int] = None
    
    @validator('membership_name')
    def validate_membership_name(cls, v):
        if v is not None and (not v or not v.strip()):
            raise ValueError('멤버십 이름은 비어있을 수 없습니다.')
        return v.strip() if v else v

class MembershipCreateRequest(BaseModel):
    id: int  # Membership ID 필수
    membership_info_id: Optional[int] = None  # Optional로 변경
    payment_amount: int
    bonus_point: int = 0
    credit: int = 0
    discount_rate: float = 0.0
    package_type: str
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    validity_period: int
    release_start_date: Optional[str] = None
    release_end_date: Optional[str] = None
    release: int = 1
    info: Optional[InfoMembershipUpdateRequest] = None  # Info 생성 정보 추가
    
    @validator('id')
    def validate_id(cls, v):
        if v <= 0:
            raise ValueError('Membership ID는 0보다 커야 합니다.')
        return v
    
    @validator('payment_amount')
    def validate_payment_amount(cls, v):
        if v <= 0:
            raise ValueError('결제 금액은 0보다 커야 합니다.')
        return v
    
    @validator('bonus_point')
    def validate_bonus_point(cls, v):
        if v < 0:
            raise ValueError('보너스 포인트는 0 이상이어야 합니다.')
        return v
    
    @validator('credit')
    def validate_credit(cls, v):
        if v < 0:
            raise ValueError('적립금은 0 이상이어야 합니다.')
        return v
    
    @validator('discount_rate')
    def validate_discount_rate(cls, v):
        if v < 0 or v > 1:
            raise ValueError('할인율은 0과 1 사이의 값이어야 합니다.')
        return v
    
    @validator('package_type')
    def validate_package_type(cls, v):
        valid_types = ['단일시술', '번들', '커스텀', '시퀀스']
        if v not in valid_types:
            raise ValueError(f'패키지 타입은 {valid_types} 중 하나여야 합니다.')
        return v
    
    @validator('validity_period')
    def validate_validity_period(cls, v):
        if v <= 0:
            raise ValueError('유효기간은 0보다 커야 합니다.')
        return v
    
    @validator('element_id', 'bundle_id', 'custom_id', 'sequence_id')
    def validate_procedure_reference(cls, v, values):
        package_type = values.get('package_type')
        if package_type == '단일시술' and not v:
            raise ValueError('단일시술 패키지의 경우 Element ID가 필요합니다.')
        elif package_type == '번들' and not v:
            raise ValueError('번들 패키지의 경우 Bundle ID가 필요합니다.')
        elif package_type == '커스텀' and not v:
            raise ValueError('커스텀 패키지의 경우 Custom ID가 필요합니다.')
        elif package_type == '시퀀스' and not v:
            raise ValueError('시퀀스 패키지의 경우 Sequence ID가 필요합니다.')
        return v

class MembershipPutRequest(BaseModel):
    """PUT 메서드용 - 모든 필드를 받아서 업데이트"""
    id: Optional[int] = None  # Membership ID 변경 지원
    membership_info_id: Optional[int] = None
    payment_amount: int
    bonus_point: int
    credit: int
    discount_rate: float
    package_type: str
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    validity_period: int
    release_start_date: Optional[str] = None
    release_end_date: Optional[str] = None
    release: int
    info: Optional[InfoMembershipUpdateRequest] = None
    
    @validator('id')
    def validate_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Membership ID는 0보다 커야 합니다.')
        return v
    
    @validator('payment_amount')
    def validate_payment_amount(cls, v):
        if v <= 0:
            raise ValueError('결제 금액은 0보다 커야 합니다.')
        return v
    
    @validator('bonus_point')
    def validate_bonus_point(cls, v):
        if v < 0:
            raise ValueError('보너스 포인트는 0 이상이어야 합니다.')
        return v
    
    @validator('credit')
    def validate_credit(cls, v):
        if v < 0:
            raise ValueError('적립금은 0 이상이어야 합니다.')
        return v
    
    @validator('discount_rate')
    def validate_discount_rate(cls, v):
        if v < 0 or v > 1:
            raise ValueError('할인율은 0과 1 사이의 값이어야 합니다.')
        return v
    
    @validator('package_type')
    def validate_package_type(cls, v):
        valid_types = ['단일시술', '번들', '커스텀', '시퀀스']
        if v not in valid_types:
            raise ValueError(f'패키지 타입은 {valid_types} 중 하나여야 합니다.')
        return v
    
    @validator('validity_period')
    def validate_validity_period(cls, v):
        if v <= 0:
            raise ValueError('유효기간은 0보다 커야 합니다.')
        return v

class MembershipUpdateRequest(BaseModel):
    id: Optional[int] = None  # Membership ID 변경 지원 추가
    membership_info_id: Optional[int] = None
    payment_amount: Optional[int] = None
    bonus_point: Optional[int] = None
    credit: Optional[int] = None
    discount_rate: Optional[float] = None
    package_type: Optional[str] = None
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    validity_period: Optional[int] = None
    release_start_date: Optional[str] = None
    release_end_date: Optional[str] = None
    release: Optional[int] = None
    info: Optional[InfoMembershipUpdateRequest] = None  # Info 수정 정보 추가
    
    @validator('id')
    def validate_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Membership ID는 0보다 커야 합니다.')
        return v
    
    @validator('payment_amount')
    def validate_payment_amount(cls, v):
        if v is not None and v <= 0:
            raise ValueError('결제 금액은 0보다 커야 합니다.')
        return v
    
    @validator('bonus_point')
    def validate_bonus_point(cls, v):
        if v is not None and v < 0:
            raise ValueError('보너스 포인트는 0 이상이어야 합니다.')
        return v
    
    @validator('credit')
    def validate_credit(cls, v):
        if v is not None and v < 0:
            raise ValueError('적립금은 0 이상이어야 합니다.')
        return v
    
    @validator('discount_rate')
    def validate_discount_rate(cls, v):
        if v is not None and (v < 0 or v > 1):
            raise ValueError('할인율은 0과 1 사이의 값이어야 합니다.')
        return v
    
    @validator('package_type')
    def validate_package_type(cls, v):
        if v is not None:
            valid_types = ['단일시술', '번들', '커스텀', '시퀀스']
            if v not in valid_types:
                raise ValueError(f'패키지 타입은 {valid_types} 중 하나여야 합니다.')
        return v
    
    @validator('validity_period')
    def validate_validity_period(cls, v):
        if v is not None and v <= 0:
            raise ValueError('유효기간은 0보다 커야 합니다.')
        return v

class InfoMembershipResponse(BaseModel):
    id: int
    membership_name: Optional[str] = None
    membership_description: Optional[str] = None
    precautions: Optional[str] = None
    release: int

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj):
        return cls(
            id=obj.ID,
            membership_name=obj.Membership_Name,
            membership_description=obj.Membership_Description,
            precautions=obj.Precautions,
            release=obj.Release
        )

class MembershipResponse(BaseModel):
    id: int
    membership_info_id: Optional[int] = None
    payment_amount: int
    bonus_point: int
    credit: int
    discount_rate: float
    package_type: str
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    validity_period: int
    release_start_date: Optional[str] = None
    release_end_date: Optional[str] = None
    release: int
    info: Optional[InfoMembershipResponse] = None  # Info 정보 포함 (id 포함)

    class Config:
        from_attributes = True
        
    @classmethod
    def from_orm(cls, obj, info=None):
        return cls(
            id=obj.ID,
            membership_info_id=obj.Membership_Info_ID,
            payment_amount=obj.Payment_Amount,
            bonus_point=obj.Bonus_Point,
            credit=obj.Credit,
            discount_rate=obj.Discount_Rate,
            package_type=obj.Package_Type,
            element_id=obj.Element_ID,
            bundle_id=obj.Bundle_ID,
            custom_id=obj.Custom_ID,
            sequence_id=obj.Sequence_ID,
            validity_period=obj.Validity_Period,
            release_start_date=obj.Release_Start_Date,
            release_end_date=obj.Release_End_Date,
            release=obj.Release,
            info=info
        )

# ============================================================================
# 트랜잭션 헬퍼 함수들
# ============================================================================

def validate_info_membership(membership_info_id: int, db: Session):
    """
    Info_Membership 존재 여부를 검증합니다.
    """
    info = db.query(InfoMembership).filter(
        InfoMembership.ID == membership_info_id,
        InfoMembership.Release == 1
    ).first()
    
    if not info:
        raise HTTPException(
            status_code=404, 
            detail=f"Info_Membership ID {membership_info_id}를 찾을 수 없습니다."
        )
    
    return info

def validate_procedure_reference(package_type: str, element_id: int = None, bundle_id: int = None, 
    custom_id: int = None, sequence_id: int = None, db: Session = None):
    """
    패키지 타입에 따른 시술 참조 유효성을 검증합니다.
    """
    if package_type == '단일시술':
        if not element_id:
            raise HTTPException(status_code=400, detail="단일시술 패키지의 경우 Element ID가 필요합니다.")
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id,
            ProcedureElement.Release == 1
        ).first()
        if not element:
            raise HTTPException(status_code=404, detail=f"Element ID {element_id}를 찾을 수 없습니다.")
    
    elif package_type == '번들':
        if not bundle_id:
            raise HTTPException(status_code=400, detail="번들 패키지의 경우 Bundle ID가 필요합니다.")
        bundle = db.query(ProcedureBundle).filter(
            ProcedureBundle.GroupID == bundle_id,
            ProcedureBundle.Release == 1
        ).first()
        if not bundle:
            raise HTTPException(status_code=404, detail=f"Bundle ID {bundle_id}를 찾을 수 없습니다.")
    
    elif package_type == '커스텀':
        if not custom_id:
            raise HTTPException(status_code=400, detail="커스텀 패키지의 경우 Custom ID가 필요합니다.")
        custom = db.query(ProcedureCustom).filter(
            ProcedureCustom.GroupID == custom_id,
            ProcedureCustom.Release == 1
        ).first()
        if not custom:
            raise HTTPException(status_code=404, detail=f"Custom ID {custom_id}를 찾을 수 없습니다.")
    
    elif package_type == '시퀀스':
        if not sequence_id:
            raise HTTPException(status_code=400, detail="시퀀스 패키지의 경우 Sequence ID가 필요합니다.")
        
        print(f"시퀀스 검증: sequence_id={sequence_id}")
        
        # 모든 시퀀스 조회해서 로그 출력
        all_sequences = db.query(ProcedureSequence).filter(
            ProcedureSequence.Release == 1
        ).all()
        print(f"Release=1인 시퀀스들: {[(s.GroupID, s.ID, s.Name) for s in all_sequences]}")
        
        sequence = db.query(ProcedureSequence).filter(
            ProcedureSequence.GroupID == sequence_id,
            ProcedureSequence.Release == 1
        ).first()
        
        if not sequence:
            raise HTTPException(status_code=404, detail=f"Sequence ID {sequence_id}를 찾을 수 없습니다.")
        
        print(f"찾은 시퀀스: {sequence.GroupID}, {sequence.ID}, {sequence.Name}")

# ============================================================================
# API 엔드포인트
# ============================================================================

@membership_router.get("/")
async def get_membership_list(db: Session = Depends(get_db)):
    """Membership 목록 조회"""
    try:
        # N+1 쿼리 문제 해결: LEFT JOIN을 사용하여 한 번의 쿼리로 모든 데이터 조회
        memberships_with_info = db.query(
            Membership,
            InfoMembership
        ).outerjoin(
            InfoMembership,
            InfoMembership.ID == Membership.Membership_Info_ID
        ).order_by(Membership.ID).all()
        
        membership_responses = []
        for membership, info in memberships_with_info:
            info_response = InfoMembershipResponse.from_orm(info) if info else None
            membership_responses.append(
                MembershipResponse.from_orm(membership, info_response)
            )
        
        return membership_responses
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Membership 목록 조회 중 오류가 발생했습니다: {str(e)}")

@membership_router.get("/{membership_id}")
async def get_membership_detail(membership_id: int, db: Session = Depends(get_db)):
    """특정 Membership 조회"""
    try:
        # Membership ID 검증
        if membership_id <= 0:
            raise HTTPException(status_code=400, detail="Membership ID는 0보다 커야 합니다.")
        
        # Membership 조회 (Release 상태와 관계없이)
        membership = db.query(Membership).filter(
            Membership.ID == membership_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=404, detail="Membership을 찾을 수 없습니다.")
        
        # Info_Membership 정보 조회
        info = None
        if membership.Membership_Info_ID:
            info = db.query(InfoMembership).filter(
                InfoMembership.ID == membership.Membership_Info_ID
            ).first()
        
        info_response = InfoMembershipResponse.from_orm(info) if info else None
        return MembershipResponse.from_orm(membership, info_response)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Membership 조회 중 오류가 발생했습니다: {str(e)}")

@membership_router.post("/")
async def create_membership(membership_data: MembershipCreateRequest, db: Session = Depends(get_db)):
    """Membership 생성"""
    try:
        # 1. Info_Membership 처리
        info_id = None
        if membership_data.info is not None:
            # Info ID 중복 확인
            existing_info = db.query(InfoMembership).filter(
                InfoMembership.ID == membership_data.info.id
            ).first()
            
            if existing_info:
                # 기존 Info 업데이트
                existing_info.Membership_Name = membership_data.info.membership_name
                existing_info.Membership_Description = membership_data.info.membership_description
                existing_info.Precautions = membership_data.info.precautions
                existing_info.Release = membership_data.info.release
                info_id = membership_data.info.id
            else:
                # 새 Info 생성
                new_info = InfoMembership(
                    ID=membership_data.info.id,
                    Membership_Name=membership_data.info.membership_name,
                    Membership_Description=membership_data.info.membership_description,
                    Precautions=membership_data.info.precautions,
                    Release=membership_data.info.release
                )
                db.add(new_info)
                info_id = membership_data.info.id
        else:
            # info가 없으면 membership_info_id 사용
            if membership_data.membership_info_id is not None:
                # membership_info_id가 존재하는지 확인
                existing_info = db.query(InfoMembership).filter(
                    InfoMembership.ID == membership_data.membership_info_id
                ).first()
                
                if existing_info:
                    # 기존 Info가 있으면 사용
                    info_id = membership_data.membership_info_id
                else:
                    # membership_info_id가 없으면 자동으로 Info 생성
                    print(f"DEBUG: membership_info_id {membership_data.membership_info_id}가 존재하지 않음, 자동 생성")
                    new_info = InfoMembership(
                        ID=membership_data.membership_info_id,
                        Membership_Name=f"멤버십 {membership_data.membership_info_id}",
                        Membership_Description=f"멤버십 {membership_data.membership_info_id} 상세 설명",
                        Precautions="",
                        Release=1
                    )
                    db.add(new_info)
                    info_id = membership_data.membership_info_id
                    print(f"DEBUG: 새로운 InfoMembership 생성 완료 - ID: {info_id}")
            else:
                raise HTTPException(status_code=400, detail="Info 정보 또는 membership_info_id가 필요합니다.")
        
        # 2. 시술 참조 유효성 검증
        validate_procedure_reference(
            membership_data.package_type,
            membership_data.element_id,
            membership_data.bundle_id,
            membership_data.custom_id,
            membership_data.sequence_id,
            db
        )
        
        # 3. Membership ID 중복 확인
        existing_membership = db.query(Membership).filter(
            Membership.ID == membership_data.id
        ).first()
        
        if existing_membership:
            raise HTTPException(
                status_code=400, 
                detail=f"Membership ID {membership_data.id}는 이미 사용 중입니다."
            )
        
        # 4. Membership 생성
        membership = Membership(
            ID=membership_data.id,
            Membership_Info_ID=info_id,
            Payment_Amount=membership_data.payment_amount,
            Bonus_Point=membership_data.bonus_point,
            Credit=membership_data.credit,
            Discount_Rate=membership_data.discount_rate,
            Package_Type=membership_data.package_type,
            Element_ID=membership_data.element_id,
            Bundle_ID=membership_data.bundle_id,
            Custom_ID=membership_data.custom_id,
            Sequence_ID=membership_data.sequence_id,
            Validity_Period=membership_data.validity_period,
            Release_Start_Date=membership_data.release_start_date,
            Release_End_Date=membership_data.release_end_date,
            Release=membership_data.release
        )
        
        db.add(membership)
        db.commit()
        db.refresh(membership)
        
        # 4. 생성된 Membership 조회하여 반환 (Info 정보 포함)
        return await get_membership_detail(membership.ID, db)
        
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
        raise HTTPException(status_code=500, detail=f"Membership 생성 중 오류가 발생했습니다: {str(e)}")

@membership_router.put("/{membership_id}")
async def update_membership(membership_id: int, membership_data: MembershipPutRequest, db: Session = Depends(get_db)):
    """Membership 수정"""
    try:
        # 1. Membership ID 검증
        if membership_id <= 0:
            raise HTTPException(status_code=400, detail="Membership ID는 0보다 커야 합니다.")
        
        # 2. 기존 Membership 조회
        membership = db.query(Membership).filter(
            Membership.ID == membership_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=404, detail="Membership을 찾을 수 없습니다.")
        
        # 3. Membership ID 변경 처리
        new_membership_id = membership_id
        if membership_data.id is not None and membership_data.id != membership_id:
            # 새로운 Membership ID 중복 확인
            existing_membership = db.query(Membership).filter(
                Membership.ID == membership_data.id
            ).first()
            
            if existing_membership:
                raise HTTPException(
                    status_code=400, 
                    detail=f"Membership ID {membership_data.id}는 이미 사용 중입니다."
                )
            
            new_membership_id = membership_data.id
        
        # 4. Info_Membership 존재 여부 검증 (membership_info_id가 변경된 경우)
        if membership_data.membership_info_id is not None:
            validate_info_membership(membership_data.membership_info_id, db)
        
        # 5. 시술 참조 유효성 검증 (패키지 타입이 변경된 경우)
        if membership_data.package_type is not None:
            validate_procedure_reference(
                membership_data.package_type,
                membership_data.element_id,
                membership_data.bundle_id,
                membership_data.custom_id,
                membership_data.sequence_id,
                db
            )
        
        # 6. Membership 정보 업데이트
        membership.Membership_Info_ID = membership_data.membership_info_id
        membership.Payment_Amount = membership_data.payment_amount
        membership.Bonus_Point = membership_data.bonus_point
        membership.Credit = membership_data.credit
        membership.Discount_Rate = membership_data.discount_rate
        membership.Package_Type = membership_data.package_type
        membership.Element_ID = membership_data.element_id
        membership.Bundle_ID = membership_data.bundle_id
        membership.Custom_ID = membership_data.custom_id
        membership.Sequence_ID = membership_data.sequence_id
        membership.Validity_Period = membership_data.validity_period
        membership.Release_Start_Date = membership_data.release_start_date
        membership.Release_End_Date = membership_data.release_end_date
        membership.Release = membership_data.release
        
        # 7. Info_Membership 정보 업데이트 (제공된 경우)
        if membership_data.info is not None:
            print(f"Info 데이터 수신: {membership_data.info}")
            
            # Info ID 결정: 요청에 있으면 사용, 없으면 기존 Membership의 Info ID 사용
            target_info_id = membership_data.info.id
            if target_info_id is None:
                target_info_id = membership.Membership_Info_ID
            print(f"Target Info ID: {target_info_id}")
            
            if target_info_id is not None:
                info = db.query(InfoMembership).filter(
                    InfoMembership.ID == target_info_id
                ).first()
                
                if info:
                    print(f"기존 Info 데이터: {info.Membership_Name}")
                    # Info ID는 변경하지 않음 (위험할 수 있음)
                    # info.ID = membership_data.info.id  # 이 줄 제거
                    info.Membership_Name = membership_data.info.membership_name
                    info.Membership_Description = membership_data.info.membership_description
                    info.Precautions = membership_data.info.precautions
                    info.Release = membership_data.info.release
                    print(f"업데이트된 Info 데이터: {info.Membership_Name}")
                    
                    # Membership의 Info ID도 업데이트 (Info ID가 변경된 경우)
                    if membership_data.info.id is not None and membership_data.info.id != membership.Membership_Info_ID:
                        membership.Membership_Info_ID = membership_data.info.id
                        print(f"Membership Info ID 업데이트: {membership.Membership_Info_ID}")
                else:
                    print(f"Info ID {target_info_id}를 찾을 수 없습니다.")
                    raise HTTPException(status_code=404, detail=f"Info ID {target_info_id}를 찾을 수 없습니다.")
            else:
                print("Target Info ID가 없습니다.")
                raise HTTPException(status_code=400, detail="Info ID가 필요합니다.")
        else:
            print("Info 데이터가 없습니다.")
        
        # 8. Membership ID 변경
        if new_membership_id != membership_id:
            membership.ID = new_membership_id
        
        # 9. Membership ID 변경 시 참조 테이블 업데이트
        if new_membership_id != membership_id:
            try:
                cascade_update_membership_id(membership_id, new_membership_id, db)
            except Exception as cascade_error:
                # 연쇄 업데이트 실패 시 로그만 남기고 계속 진행
                print(f"Membership ID 변경 후 연쇄 업데이트 실패: {str(cascade_error)}")
        
        # 10. 트랜잭션 커밋
        db.commit()
        db.refresh(membership)
        
        # 11. 수정된 Membership 조회하여 반환 (Info 정보 포함)
        return await get_membership_detail(new_membership_id, db)
        
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
        raise HTTPException(status_code=500, detail=f"Membership 수정 중 오류가 발생했습니다: {str(e)}")

@membership_router.delete("/{membership_id}")
async def delete_membership(membership_id: int, db: Session = Depends(get_db)):
    """Membership 삭제"""
    try:
        # 1. Membership ID 검증
        if membership_id <= 0:
            raise HTTPException(status_code=400, detail="Membership ID는 0보다 커야 합니다.")
        
        # 2. Membership 조회
        membership = db.query(Membership).filter(
            Membership.ID == membership_id
        ).first()
        
        if not membership:
            raise HTTPException(status_code=404, detail="Membership을 찾을 수 없습니다.")
        
        # 3. Membership 삭제
        db.delete(membership)
        db.commit()
        
        return {
            "status": "success",
            "message": f"Membership ID {membership_id}가 성공적으로 삭제되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Membership 삭제 중 오류가 발생했습니다: {str(e)}")

@membership_router.put("/{membership_id}/deactivate")
async def deactivate_membership(membership_id: int, db: Session = Depends(get_db)):
    """Membership 비활성화"""
    try:
        # 1. Membership ID 검증
        if membership_id <= 0:
            raise HTTPException(status_code=400, detail="Membership ID는 0보다 커야 합니다.")
        
        # 2. Membership 조회
        membership = db.query(Membership).filter(
            Membership.ID == membership_id,
            Membership.Release == 1
        ).first()
        
        if not membership:
            raise HTTPException(status_code=404, detail="활성화된 Membership을 찾을 수 없습니다.")
        
        # 3. Membership 비활성화
        membership.Release = 0
        db.commit()
        
        return {
            "status": "success",
            "message": f"Membership ID {membership_id}가 비활성화되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Membership 비활성화 중 오류가 발생했습니다: {str(e)}")

@membership_router.put("/{membership_id}/activate")
async def activate_membership(membership_id: int, db: Session = Depends(get_db)):
    """Membership 활성화"""
    try:
        # 1. Membership ID 검증
        if membership_id <= 0:
            raise HTTPException(status_code=400, detail="Membership ID는 0보다 커야 합니다.")
        
        # 2. 비활성화된 Membership 조회
        membership = db.query(Membership).filter(
            Membership.ID == membership_id,
            Membership.Release == 0
        ).first()
        
        if not membership:
            raise HTTPException(status_code=404, detail="비활성화된 Membership을 찾을 수 없습니다.")
        
        # 3. Membership 활성화
        membership.Release = 1
        db.commit()
        
        return {
            "status": "success",
            "message": f"Membership ID {membership_id}가 활성화되었습니다."
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
        raise HTTPException(status_code=500, detail=f"Membership 활성화 중 오류가 발생했습니다: {str(e)}")
