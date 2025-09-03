"""
Product 관련 공통 모델과 유틸리티 함수들
"""

from pydantic import BaseModel, validator
from typing import Optional, List, Union
from fastapi import HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, String
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence
from db.models.info import InfoStandard, InfoEvent


# ============================================================================
# 공통 요청/응답 모델들
# ============================================================================

class ProductUpdateRequest(BaseModel):
    """Product 전체 수정 요청 (모든 컬럼 수정 가능)"""
    # 기본 정보
    new_id: Optional[int] = None  # Product ID 변경
    release: Optional[int] = None
    package_type: Optional[str] = None
    
    # 시술 참조 ID (하나만 설정 가능)
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    
    # Info 참조 ID
    standard_info_id: Optional[int] = None
    event_info_id: Optional[int] = None
    
    # 가격 정보
    sell_price: Optional[int] = None
    original_price: Optional[int] = None
    discount_rate: Optional[float] = None
    procedure_cost: Optional[int] = None
    margin: Optional[int] = None
    margin_rate: Optional[float] = None
    
    # 날짜 정보
    start_date: Optional[str] = None  # Standard_Start_Date 또는 Event_Start_Date
    end_date: Optional[str] = None    # Standard_End_Date 또는 Event_End_Date
    
    # 기타 정보
    validity_period: Optional[int] = None
    vat: Optional[int] = None
    covered_type: Optional[str] = None
    taxable_type: Optional[str] = None
    
    # Info_Standard 정보 (ProductStandard인 경우)
    info_standard_id: Optional[int] = None
    product_standard_name: Optional[str] = None
    product_standard_description: Optional[str] = None
    precautions: Optional[str] = None
    
    # Info_Event 정보 (ProductEvent인 경우)
    event_info_id: Optional[int] = None
    event_name: Optional[str] = None
    event_description: Optional[str] = None
    event_precautions: Optional[str] = None
    
    @validator('new_id')
    def validate_new_id(cls, v):
        if v is not None and v <= 0:
            raise ValueError('새로운 Product ID는 0보다 커야 합니다.')
        return v
    
    @validator('package_type')
    def validate_package_type(cls, v):
        if v and v not in ["단일시술", "번들", "커스텀", "시퀀스"]:
            raise ValueError('Package Type은 "단일시술", "번들", "커스텀", "시퀀스" 중 하나여야 합니다.')
        return v
    
    @validator('element_id', 'bundle_id', 'custom_id', 'sequence_id')
    def validate_procedure_reference(cls, v, values):
        # 시술 참조는 하나만 설정되어야 함
        reference_count = sum([
            1 if values.get('element_id') is not None else 0,
            1 if values.get('bundle_id') is not None else 0,
            1 if values.get('custom_id') is not None else 0,
            1 if values.get('sequence_id') is not None else 0
        ])
        
        if reference_count > 1:
            raise ValueError('시술 참조는 하나만 설정할 수 있습니다.')
        
        return v
    
    @validator('sell_price', 'original_price', 'procedure_cost', 'margin')
    def validate_positive_integers(cls, v):
        if v is not None and v < 0:
            raise ValueError('가격과 비용은 0 이상이어야 합니다.')
        return v
    
    @validator('discount_rate', 'margin_rate')
    def validate_rates(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('비율은 0~100 사이여야 합니다.')
        return v


class ProductInfoResponse(BaseModel):
    """Product Info 응답 모델 (목록 조회용)"""
    type: str  # "standard" 또는 "event"
    id: int
    name: str
    description: str
    precautions: Optional[str] = None


# ============================================================================
# 공통 유틸리티 함수들
# ============================================================================

def get_procedure_info(product, db: Session) -> dict:
    """Product의 시술 정보 조회 (상세 조회용)"""
    try:
        if hasattr(product, 'Element_ID') and product.Element_ID:
            print(f"DEBUG: Processing Element_ID: {product.Element_ID}")
            return validate_procedure_reference("단일시술", element_id=product.Element_ID, db=db)
        elif hasattr(product, 'Bundle_ID') and product.Bundle_ID:
            print(f"DEBUG: Processing Bundle_ID: {product.Bundle_ID}")
            return validate_procedure_reference("번들", bundle_id=product.Bundle_ID, db=db)
        elif hasattr(product, 'Custom_ID') and product.Custom_ID:
            print(f"DEBUG: Processing Custom_ID: {product.Custom_ID}")
            return validate_procedure_reference("커스텀", custom_id=product.Custom_ID, db=db)
        elif hasattr(product, 'Sequence_ID') and product.Sequence_ID:
            print(f"DEBUG: Processing Sequence_ID: {product.Sequence_ID}")
            return validate_procedure_reference("시퀀스", sequence_id=product.Sequence_ID, db=db)
        else:
            print("DEBUG: No procedure reference found")
            return {"type": "unknown", "id": 0, "name": "Unknown", "description": "Unknown"}
    except Exception as e:
        print(f"DEBUG: Error in get_procedure_info: {str(e)}")
        return {"type": "unknown", "id": 0, "name": "Unknown", "description": f"Error: {str(e)}"}


def validate_procedure_reference(
    package_type: str,
    element_id: Optional[int] = None,
    bundle_id: Optional[int] = None,
    custom_id: Optional[int] = None,
    sequence_id: Optional[int] = None,
    db: Session = None
) -> dict:
    """
    시술 참조 검증 및 정보 조회
    
    Args:
        package_type: 시술 타입 ("단일시술", "번들", "커스텀", "시퀀스")
        element_id, bundle_id, custom_id, sequence_id: 참조할 시술 ID
        db: 데이터베이스 세션
    
    Returns:
        dict: 시술 정보 (name, description, procedure_cost 등)
    
    Raises:
        HTTPException: 시술이 존재하지 않거나 Release=0인 경우
    """
    try:
        if package_type == "단일시술":
            if element_id is None:
                raise HTTPException(status_code=400, detail="Element ID가 필요합니다.")
            
            # 디버깅을 위한 로그 추가
            print(f"DEBUG: Searching for Element ID: {element_id}")
            
            # 먼저 Release 조건 없이 조회
            element_all = db.query(ProcedureElement).filter(
                ProcedureElement.ID == element_id
            ).first()
            
            if element_all:
                print(f"DEBUG: Found Element (Release: {element_all.Release}): {element_all.Name}")
            else:
                print(f"DEBUG: Element ID {element_id} not found in ProcedureElement table")
            
            # Release = 1인 Element만 조회
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == element_id,
                ProcedureElement.Release == 1
            ).first()
            
            if not element:
                # 더 자세한 오류 메시지 제공
                if element_all:
                    raise HTTPException(status_code=400, detail=f"Element ID {element_id}는 존재하지만 비활성화되어 있습니다 (Release: {element_all.Release})")
                else:
                    raise HTTPException(status_code=404, detail=f"Element ID {element_id}를 찾을 수 없습니다. ProcedureElement 테이블에 해당 ID가 존재하지 않습니다.")
            
            return {
                "type": "element",
                "id": element.ID,
                "name": element.Name,
                "description": element.Description,  # 수정: description -> Description
                "procedure_cost": element.Procedure_Cost,
                "category": f"{element.Class_Major} > {element.Class_Sub} > {element.Class_Detail}",
                "class_type": element.Class_Type,
                "class_major": element.Class_Major,
                "class_sub": element.Class_Sub,
                "class_detail": element.Class_Detail,
                "position_type": element.Position_Type,
                "cost_time": element.Cost_Time,
                "plan_state": element.Plan_State,
                "plan_count": element.Plan_Count,
                "plan_interval": element.Plan_Interval,
                "consum_1_id": element.Consum_1_ID,
                "consum_1_count": element.Consum_1_Count,
                "procedure_level": element.Procedure_Level,
                "price": element.Price,
                "release": element.Release
            }
            
        elif package_type == "번들":
            if bundle_id is None:
                raise HTTPException(status_code=400, detail="Bundle ID가 필요합니다.")
            
            bundle = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == bundle_id,
                ProcedureBundle.Release == 1
            ).first()
            
            if not bundle:
                raise HTTPException(status_code=404, detail=f"Bundle ID {bundle_id}를 찾을 수 없습니다.")
            
            return {
                "type": "bundle",
                "id": bundle.GroupID,
                "name": bundle.Name,
                "description": f"번들 시술 (Element ID: {bundle.Element_ID})",
                "element_id": bundle.Element_ID,
                "element_cost": bundle.Element_Cost,
                "price_ratio": bundle.Price_Ratio,
                "release": bundle.Release
            }
            
        elif package_type == "커스텀":
            if custom_id is None:
                raise HTTPException(status_code=400, detail="Custom ID가 필요합니다.")
            
            custom = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == custom_id,
                ProcedureCustom.Release == 1
            ).first()
            
            if not custom:
                raise HTTPException(status_code=404, detail=f"Custom ID {custom_id}를 찾을 수 없습니다.")
            
            return {
                "type": "custom",
                "id": custom.GroupID,
                "name": custom.Name,
                "description": f"커스텀 시술 (Element ID: {custom.Element_ID})",
                "element_id": custom.Element_ID,
                "element_cost": custom.Element_Cost,
                "custom_count": custom.Custom_Count,
                "price_ratio": custom.Price_Ratio,
                "release": custom.Release
            }
            
        elif package_type == "시퀀스":
            if sequence_id is None:
                raise HTTPException(status_code=400, detail="Sequence ID가 필요합니다.")
            
            sequence = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == sequence_id,
                ProcedureSequence.Release == 1
            ).first()
            
            if not sequence:
                raise HTTPException(status_code=404, detail=f"Sequence ID {sequence_id}를 찾을 수 없습니다.")
            
            return {
                "type": "sequence",
                "id": sequence.GroupID,
                "name": sequence.Name,
                "description": f"시퀀스 시술 (Step {sequence.Step_Num})",
                "step_num": sequence.Step_Num,
                "element_id": sequence.Element_ID,
                "bundle_id": sequence.Bundle_ID,
                "custom_id": sequence.Custom_ID,
                "sequence_interval": sequence.Sequence_Interval,
                "procedure_cost": sequence.Procedure_Cost,
                "price_ratio": sequence.Price_Ratio,
                "release": sequence.Release
            }
            
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 시술 타입입니다: {package_type}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시술 정보 조회 중 오류가 발생했습니다: {str(e)}")


def get_product_info(product, db: Session) -> Optional[dict]:
    """Product의 Info 정보 조회"""
    try:
        if hasattr(product, 'Standard_Info_ID') and product.Standard_Info_ID:
            info = db.query(InfoStandard).filter(
                InfoStandard.ID == product.Standard_Info_ID,
                InfoStandard.Release == 1
            ).first()
            
            if info:
                return {
                    "id": info.ID,
                    "name": info.Product_Standard_Name,
                    "description": info.Product_Standard_Description,
                    "precautions": info.Precautions
                }
                
        elif hasattr(product, 'Event_Info_ID') and product.Event_Info_ID:
            info = db.query(InfoEvent).filter(
                InfoEvent.ID == product.Event_Info_ID,
                InfoEvent.Release == 1
            ).first()
            
            if info:
                return {
                    "id": info.ID,
                    "name": info.Event_Name,
                    "description": info.Event_Description,
                    "precautions": info.Precautions
                }
                
        return None
        
    except Exception as e:
        print(f"DEBUG: Error in get_product_info: {str(e)}")
        return None


def calculate_product_margin(sell_price: int, procedure_cost: int) -> dict:
    """
    Product 마진 계산
    
    Args:
        sell_price: 판매가
        procedure_cost: 시술 비용
    
    Returns:
        dict: 마진 정보 (margin, margin_rate)
    """
    margin = sell_price - procedure_cost
    margin_rate = (margin / sell_price * 100) if sell_price > 0 else 0
    
    return {
        "margin": margin,
        "margin_rate": round(margin_rate, 2),
        "procedure_cost": procedure_cost,
        "sell_price": sell_price
    }


# ============================================================================
# 공통 목록 조회 API
# ============================================================================

def get_products_list_common(
    product_type: str,
    db: Session,
    search: Optional[str] = None,
    covered_type: Optional[str] = None,
    taxable_type: Optional[str] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None
) -> dict:
    """Product 목록 조회 공통 함수"""
    try:
        if product_type == "standard":
            from db.models.product import ProductStandard
            ProductModel = ProductStandard
            start_date_field = "Standard_Start_Date"
            end_date_field = "Standard_End_Date"
        elif product_type == "event":
            from db.models.product import ProductEvent
            ProductModel = ProductEvent
            start_date_field = "Event_Start_Date"
            end_date_field = "Event_End_Date"
        else:
            raise ValueError(f"지원하지 않는 product_type: {product_type}")
        
        # 기본 쿼리 설정
        query = db.query(ProductModel).filter(ProductModel.Release == 1)
        
        # 검색 필터 적용
        if search:
            query = query.filter(
                or_(
                    ProductModel.ID.cast(String).contains(search),
                    ProductModel.Package_Type.contains(search)
                )
            )
        
        if covered_type:
            query = query.filter(ProductModel.Covered_Type == covered_type)
        
        if taxable_type:
            query = query.filter(ProductModel.Taxable_Type == taxable_type)
        
        if min_price is not None:
            query = query.filter(ProductModel.Sell_Price >= min_price)
        
        if max_price is not None:
            query = query.filter(ProductModel.Sell_Price <= max_price)
        
        # 결과 조회
        products = query.all()
        
        data = []
        for product in products:
            # Info 정보 조회
            info = get_product_info(product, db)
            
            product_data = {
                "id": product.ID,
                "type": product_type,
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": getattr(product, start_date_field),
                "end_date": getattr(product, end_date_field),
                "covered_type": product.Covered_Type,
                "taxable_type": product.Taxable_Type,
                "procedure_cost": product.Procedure_Cost,
                "margin": product.Margin,
                "margin_rate": product.Margin_Rate,
                "release": product.Release,
                "package_type": product.Package_Type,
                "element_id": product.Element_ID,
                "bundle_id": product.Bundle_ID,
                "custom_id": product.Custom_ID,
                "sequence_id": product.Sequence_ID,
                "info": info
            }
            
            if product_type == "standard":
                product_data["standard_info_id"] = getattr(product, "Standard_Info_ID", None)
                product_data["info_standard"] = info
            else:
                product_data["event_info_id"] = getattr(product, "Event_Info_ID", None)
                product_data["info_event"] = info
            
            data.append(product_data)
        
        return {
            "status": "success",
            "message": f"{product_type.capitalize()} Product 목록 조회 완료",
            "data": data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"{product_type.capitalize()} Product 목록 조회 중 오류가 발생했습니다: {str(e)}")
