"""
    Product CRUD API
    
    이 모듈은 Product의 생성, 조회, 수정, 삭제 기능을 제공합니다.
    Standard와 Event Product를 동시에 관리하며, 시술과의 복잡한 관계를 처리합니다.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy import or_, func
from typing import Optional, List, Union
from pydantic import BaseModel, validator
from datetime import datetime, timedelta

from db.session import get_db
from db.models.product import ProductStandard, ProductEvent
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence
from db.models.info import InfoStandard, InfoEvent
from db.models.consumables import Consumables

# 라우터 설정
products_router = APIRouter(
    prefix="/admin/products",
    tags=["Products"]
)

# ============================================================================
# Pydantic 모델 (기본 구조)
# ============================================================================

class ProcedureInfoRequest(BaseModel):
    """시술 참조 정보"""
    id: int  # ID (인덱스)
    release: int = 1  # Release (릴리즈)
    package_type: str  # "단일시술", "번들", "커스텀", "시퀀스"
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    standard_info_id: Optional[int] = None  # Standard_Info_ID
    event_info_id: Optional[int] = None  # Event_Info_ID
    procedure_grade: Optional[str] = None  # Procedure_Grade (지정정보)
    
    @validator('package_type')
    def validate_package_type(cls, v):
        valid_types = ["단일시술", "번들", "커스텀", "시퀀스"]
        if v not in valid_types:
            raise ValueError(f'Package Type은 {valid_types} 중 하나여야 합니다.')
        return v

class StandardSettingsRequest(BaseModel):
    """Standard Product 설정"""
    enabled: bool = False
    procedure_cost: Optional[int] = None  # Procedure_Cost (원가)
    sell_price: Optional[int] = None  # Sell_Price (실 판매가)
    original_price: Optional[int] = None  # Original_Price (정상가)
    vat: Optional[int] = None  # VAT (부가세)
    discount_rate: Optional[float] = None  # Discount_Rate (할인율)
    margin: Optional[int] = None  # Margin (마진값)
    margin_rate: Optional[float] = None  # Margin_Rate (마진율)
    start_date: Optional[str] = None  # Standard_Start_Date
    end_date: Optional[str] = None  # Standard_End_Date
    validity_period: Optional[int] = None  # Validity_Period (유효기간)
    covered_type: Optional[str] = None  # Covered_Type (급여분류)
    taxable_type: Optional[str] = None  # Taxable_Type (과세분류)
    standard_info_id: Optional[int] = None
    
    # Info 관련 필드들
    product_standard_name: Optional[str] = None  # Product_Standard_Name
    product_standard_description: Optional[str] = None  # Product_Standard_Description
    precautions: Optional[str] = None  # Precautions
    
    @validator('sell_price')
    def validate_sell_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('판매가는 0보다 커야 합니다.')
        return v

class EventSettingsRequest(BaseModel):
    """Event Product 설정"""
    enabled: bool = False
    procedure_cost: Optional[int] = None  # Procedure_Cost (원가)
    sell_price: Optional[int] = None  # Sell_Price (실 판매가)
    original_price: Optional[int] = None  # Original_Price (정상가)
    vat: Optional[int] = None  # VAT (부가세)
    discount_rate: Optional[float] = None  # Discount_Rate (할인율)
    margin: Optional[int] = None  # Margin (마진값)
    margin_rate: Optional[float] = None  # Margin_Rate (마진율)
    start_date: Optional[str] = None  # Event_Start_Date
    end_date: Optional[str] = None  # Event_End_Date
    validity_period: Optional[int] = None  # Validity_Period (유효기간)
    covered_type: Optional[str] = None  # Covered_Type (급여분류)
    taxable_type: Optional[str] = None  # Taxable_Type (과세분류)
    event_info_id: Optional[int] = None
    
    # Info 관련 필드들
    event_name: Optional[str] = None  # Event_Name
    event_description: Optional[str] = None  # Event_Description
    event_precautions: Optional[str] = None  # Precautions
    
    @validator('sell_price')
    def validate_sell_price(cls, v):
        if v is not None and v <= 0:
            raise ValueError('판매가는 0보다 커야 합니다.')
        return v
    
    @validator('discount_rate')
    def validate_discount_rate(cls, v):
        if v is not None and (v < 0 or v > 100):
            raise ValueError('할인율은 0~100 사이여야 합니다.')
        return v

class ProductCreateRequest(BaseModel):
    """Product 생성 요청"""
    procedure_info: ProcedureInfoRequest
    standard_settings: StandardSettingsRequest
    event_settings: EventSettingsRequest
    
    @validator('procedure_info')
    def validate_procedure_info(cls, v):
        # Element, Bundle, Custom, Sequence 중 하나만 선택되어야 함
        reference_count = sum([
            1 if v.element_id is not None else 0,
            1 if v.bundle_id is not None else 0,
            1 if v.custom_id is not None else 0,
            1 if v.sequence_id is not None else 0
        ])
        
        if reference_count != 1:
            raise ValueError('Element, Bundle, Custom, Sequence 중 정확히 하나만 선택해야 합니다.')
        
        return v
    
    @validator('standard_settings', 'event_settings')
    def validate_settings(cls, v):
        if v and v.enabled:
            if v.sell_price is None or v.sell_price <= 0:
                raise ValueError('활성화된 Product는 판매가가 필요합니다.')
            # 날짜는 옵셔널로 처리 (자동으로 오늘 날짜부터 2개월 후까지 설정)
        
        return v

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

# ============================================================================
# Product 조회 응답 모델들
# ============================================================================

class ProductInfoResponse(BaseModel):
    """Product Info 응답 모델 (목록 조회용)"""
    type: str  # "standard" 또는 "event"
    id: int
    name: str
    description: str
    precautions: Optional[str] = None

class ProductListResponse(BaseModel):
    """Product 목록 조회 응답 모델"""
    id: int
    type: str  # "standard" 또는 "event"
    sell_price: int
    original_price: int
    discount_rate: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    covered_type: Optional[str] = None
    taxable_type: Optional[str] = None
    procedure_cost: Optional[int] = None
    margin: Optional[int] = None
    margin_rate: Optional[float] = None
    release: int
    package_type: Optional[str] = None
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    standard_info_id: Optional[int] = None
    event_info_id: Optional[int] = None
    info_standard: Optional[ProductInfoResponse] = None
    info_event: Optional[ProductInfoResponse] = None

class ProductDetailResponse(BaseModel):
    """Product 상세 조회 응답 모델"""
    id: int
    sell_price: int
    original_price: int
    discount_rate: float
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    validity_period: Optional[int] = None
    vat: Optional[int] = None
    covered_type: Optional[str] = None
    taxable_type: Optional[str] = None
    procedure_cost: Optional[int] = None
    margin: Optional[int] = None
    margin_rate: Optional[float] = None
    release: int
    package_type: Optional[str] = None
    element_id: Optional[int] = None
    bundle_id: Optional[int] = None
    custom_id: Optional[int] = None
    sequence_id: Optional[int] = None
    standard_info_id: Optional[int] = None
    event_info_id: Optional[int] = None
    info_standard: Optional[ProductInfoResponse] = None
    info_event: Optional[ProductInfoResponse] = None
    procedure_info: Optional[dict] = None  # 시술 정보 (상세 조회용)
    procedure_detail: Optional[dict] = None  # 연결된 시술 상세 정보

class ProductGroupedResponse(BaseModel):
    """시술별 그룹화된 Product 응답 모델"""
    procedure_info: dict  # 시술 정보
    products: dict  # {"standard": [], "event": []}

class ProductListApiResponse(BaseModel):
    """Product 목록 조회 API 응답 모델"""
    status: str
    message: str
    data: List[Union[ProductListResponse, ProductGroupedResponse]]

class ProductListPaginatedResponse(BaseModel):
    """Product 목록 조회 API 응답 모델"""
    status: str
    message: str
    data: List[Union[ProductListResponse, ProductGroupedResponse]]

class ProductDetailApiResponse(BaseModel):
    """Product 상세 조회 API 응답 모델"""
    status: str
    message: str
    data: ProductDetailResponse

class ProductResponse(BaseModel):
    """Product 응답 모델 (기존 호환성용)"""
    id: int
    sell_price: int
    original_price: int
    discount_rate: float
    start_date: Optional[str]
    end_date: Optional[str]
    covered_type: Optional[str]
    taxable_type: Optional[str]
    procedure_cost: Optional[int] = None
    margin: Optional[int] = None
    margin_rate: Optional[float] = None
    release: int
    
    class Config:
        from_attributes = True

# ============================================================================
# 기본 API 엔드포인트 (구조만)
# ============================================================================

@products_router.get("/", response_model=ProductListPaginatedResponse)
async def get_products_list(
    view_type: str = Query("procedure_grouped", description="조회 타입 (procedure_grouped, all)"),
    product_type: Optional[str] = Query(None, description="Product 타입 (standard, event)"),
    search: Optional[str] = Query(None, description="검색어"),
    covered_type: Optional[str] = Query(None, description="급여분류 (급여, 비급여)"),
    taxable_type: Optional[str] = Query(None, description="과세분류 (과세, 면세)"),
    min_price: Optional[int] = Query(None, description="최소 판매가"),
    max_price: Optional[int] = Query(None, description="최대 판매가"),
    db: Session = Depends(get_db)
):
    """Product 목록 조회"""
    try:
        # 1. 기본 쿼리 설정 (Release 상태와 관계없이)
        standard_query = db.query(ProductStandard)
        event_query = db.query(ProductEvent)
        
        # 2. Product 타입 필터링
        if product_type == "standard":
            # Standard만 조회하므로 Event 쿼리는 None으로 설정
            event_query = None
            print("Standard 상품만 조회하도록 설정")
        elif product_type == "event":
            # Event만 조회하므로 Standard 쿼리는 None으로 설정
            standard_query = None
            print("Event 상품만 조회하도록 설정")
        else:
            print("모든 상품 타입 조회")
        
        # 3. 검색어 필터링 (시술 정보와 연관)
        if search:
            # Element, Bundle, Custom, Sequence에서 검색 (Release 상태와 관계없이)
            search_elements = db.query(ProcedureElement.ID).filter(
                ProcedureElement.Name.contains(search)
            ).subquery()
            
            search_bundles = db.query(ProcedureBundle.GroupID).filter(
                ProcedureBundle.Name.contains(search)
            ).subquery()
            
            search_customs = db.query(ProcedureCustom.GroupID).filter(
                ProcedureCustom.Name.contains(search)
            ).subquery()
            
            search_sequences = db.query(ProcedureSequence.GroupID).subquery()
            
            standard_query = standard_query.filter(
                or_(
                    ProductStandard.Element_ID.in_(search_elements),
                    ProductStandard.Bundle_ID.in_(search_bundles),
                    ProductStandard.Custom_ID.in_(search_customs),
                    ProductStandard.Sequence_ID.in_(search_sequences)
                )
            )
            
            if event_query is not None:
                event_query = event_query.filter(
                    or_(
                        ProductEvent.Element_ID.in_(search_elements),
                        ProductEvent.Bundle_ID.in_(search_bundles),
                        ProductEvent.Custom_ID.in_(search_customs),
                        ProductEvent.Sequence_ID.in_(search_sequences)
                    )
                )
        
        # 4. 추가 필터링
        print(f"=== 추가 필터링 적용 ===")
        if covered_type:
            standard_query = standard_query.filter(ProductStandard.Covered_Type == covered_type)
            if event_query is not None:
                event_query = event_query.filter(ProductEvent.Covered_Type == covered_type)
            print(f"covered_type 필터 적용: {covered_type}")
        
        if taxable_type:
            standard_query = standard_query.filter(ProductStandard.Taxable_Type == taxable_type)
            if event_query is not None:
                event_query = event_query.filter(ProductEvent.Taxable_Type == taxable_type)
            print(f"taxable_type 필터 적용: {taxable_type}")
        
        if min_price is not None:
            standard_query = standard_query.filter(ProductStandard.Sell_Price >= min_price)
            if event_query is not None:
                event_query = event_query.filter(ProductEvent.Sell_Price >= min_price)
            print(f"min_price 필터 적용: {min_price}")
        
        if max_price is not None:
            standard_query = standard_query.filter(ProductStandard.Sell_Price <= max_price)
            if event_query is not None:
                event_query = event_query.filter(ProductEvent.Sell_Price <= max_price)
            print(f"max_price 필터 적용: {max_price}")
        
        print(f"=== 필터링 후 쿼리 상태 ===")
        print(f"standard_query: {standard_query}")
        print(f"event_query: {event_query}")
        
        if view_type == "procedure_grouped":
            # 시술별로 그룹화된 조회
            products_data = await get_products_grouped_by_procedure(
                standard_query, event_query, db
            )
        else:
            # 전체 목록 조회
            products_data = await get_all_products(
                standard_query, event_query, db
            )
        
        return {
            "status": "success",
            "message": "Product 목록 조회 완료",
            "data": products_data["products"]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product 목록 조회 중 오류가 발생했습니다: {str(e)}")

@products_router.post("/")
async def create_product(product_data: ProductCreateRequest, db: Session = Depends(get_db)):
    """Product 생성 (Standard/Event 동시 생성)"""
    try:
        # 1. 시술 참조 검증 및 정보 조회
        procedure_info = validate_procedure_reference(
            package_type=product_data.procedure_info.package_type,
            element_id=product_data.procedure_info.element_id,
            bundle_id=product_data.procedure_info.bundle_id,
            custom_id=product_data.procedure_info.custom_id,
            sequence_id=product_data.procedure_info.sequence_id,
            db=db
        )
        
        # procedure_info에 추가 정보 포함
        procedure_info.update({
            "id": product_data.procedure_info.id,
            "release": product_data.procedure_info.release,
            "package_type": product_data.procedure_info.package_type,
            "element_id": product_data.procedure_info.element_id,
            "bundle_id": product_data.procedure_info.bundle_id,
            "custom_id": product_data.procedure_info.custom_id,
            "sequence_id": product_data.procedure_info.sequence_id,
            "standard_info_id": product_data.procedure_info.standard_info_id,
            "event_info_id": product_data.procedure_info.event_info_id,
            "procedure_grade": product_data.procedure_info.procedure_grade
        })
        
        print(f"DEBUG: procedure_info 업데이트 후: {procedure_info}")
        print(f"DEBUG: product_data.procedure_info.id: {product_data.procedure_info.id}")
        print(f"DEBUG: product_data.procedure_info.standard_info_id: {product_data.procedure_info.standard_info_id}")
        
        created_products = {}
        
        # 2. Standard Product 생성 (활성화된 경우)
        if product_data.standard_settings.enabled:
            try:
                standard_product = create_standard_product(
                    procedure_info=procedure_info,
                    settings=product_data.standard_settings,
                    db=db
                )
                
                # Info_Standard 정보 조회
                info_standard = None
                if standard_product.Standard_Info_ID:
                    info_standard = db.query(InfoStandard).filter(
                        InfoStandard.ID == standard_product.Standard_Info_ID
                    ).first()
                
                created_products["standard"] = {
                    "id": standard_product.ID,
                    "sell_price": standard_product.Sell_Price,
                    "original_price": standard_product.Original_Price,
                    "procedure_cost": standard_product.Procedure_Cost,
                    "vat": standard_product.VAT,
                    "margin": standard_product.Margin,
                    "margin_rate": standard_product.Margin_Rate,
                    "discount_rate": standard_product.Discount_Rate,
                    "info": {
                        "id": info_standard.ID if info_standard else None,
                        "name": info_standard.Product_Standard_Name if info_standard else None,
                        "description": info_standard.Product_Standard_Description if info_standard else None,
                        "precautions": info_standard.Precautions if info_standard else None
                    } if info_standard else None
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Standard Product 생성 실패: {str(e)}")
        
        # 3. Event Product 생성 (활성화된 경우)
        if product_data.event_settings.enabled:
            try:
                event_product = create_event_product(
                    procedure_info=procedure_info,
                    settings=product_data.event_settings,
                    db=db
                )
                
                # Info_Event 정보 조회
                info_event = None
                if event_product.Event_Info_ID:
                    info_event = db.query(InfoEvent).filter(
                        InfoEvent.ID == event_product.Event_Info_ID
                    ).first()
                
                created_products["event"] = {
                    "id": event_product.ID,
                    "sell_price": event_product.Sell_Price,
                    "original_price": event_product.Original_Price,
                    "procedure_cost": event_product.Procedure_Cost,
                    "vat": event_product.VAT,
                    "discount_rate": event_product.Discount_Rate,
                    "margin": event_product.Margin,
                    "margin_rate": event_product.Margin_Rate,
                    "info": {
                        "id": info_event.ID if info_event else None,
                        "name": info_event.Event_Name if info_event else None,
                        "description": info_event.Event_Description if info_event else None,
                        "precautions": info_event.Precautions if info_event else None
                    } if info_event else None
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Event Product 생성 실패: {str(e)}")
        
        # 4. 트랜잭션 커밋
        try:
            db.commit()
            print(f"DEBUG: 트랜잭션 커밋 성공")
        except IntegrityError as e:
            db.rollback()
            print(f"DEBUG: 데이터 무결성 오류: {str(e)}")
            raise HTTPException(status_code=400, detail=f"데이터 무결성 오류: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            print(f"DEBUG: 데이터베이스 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        except Exception as e:
            db.rollback()
            print(f"DEBUG: 예상치 못한 오류: {str(e)}")
            raise HTTPException(status_code=500, detail=f"예상치 못한 오류: {str(e)}")
        
        return {
            "status": "success",
            "message": "Product가 성공적으로 생성되었습니다.",
            "procedure_info": procedure_info,
            "created_products": created_products
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Product 생성 중 오류가 발생했습니다: {str(e)}")

@products_router.get("/standard/{product_id}", response_model=ProductDetailApiResponse)
async def get_standard_product(product_id: int, db: Session = Depends(get_db)):
    """Standard Product 상세 조회"""
    try:
        product = db.query(ProductStandard).filter(
            ProductStandard.ID == product_id,
            ProductStandard.Release == 1
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Standard Product ID {product_id}를 찾을 수 없습니다.")
        
        # Info 정보 조회
        info_standard = get_product_info(product, db)
        
        # Procedure 정보 조회
        procedure_info = get_procedure_info(product, db)
        
        # 연결된 시술 상세 정보 조회
        procedure_detail = None
        if product.Element_ID:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == product.Element_ID,
                ProcedureElement.Release == 1
            ).first()
            if element:
                procedure_detail = {
                    "type": "element",
                    "id": element.ID,
                    "name": element.Name,
                    "description": element.description,
                    "class_major": element.Class_Major,
                    "class_sub": element.Class_Sub,
                    "class_detail": element.Class_Detail,
                    "class_type": element.Class_Type,
                    "position_type": element.Position_Type,
                    "cost_time": element.Cost_Time,
                    "plan_state": element.Plan_State,
                    "plan_count": element.Plan_Count,
                    "plan_interval": element.Plan_Interval,
                    "consum_1_id": element.Consum_1_ID,
                    "consum_1_count": element.Consum_1_Count,
                    "procedure_level": element.Procedure_Level,
                    "procedure_cost": element.Procedure_Cost,
                    "price": element.Price,
                    "release": element.Release
                }
        elif product.Bundle_ID:
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == product.Bundle_ID,
                ProcedureBundle.Release == 1
            ).all()
            if bundles:
                first_bundle = bundles[0]
                procedure_detail = {
                    "type": "bundle",
                    "id": product.Bundle_ID,
                    "name": first_bundle.Name,
                    "description": f"번들 시술 (총 {len(bundles)}개 Element 포함)",
                    "element_count": len(bundles),
                    "bundles": [
                        {
                            "id": bundle.ID,
                            "element_id": bundle.Element_ID,
                            "element_cost": bundle.Element_Cost,
                            "price_ratio": bundle.Price_Ratio,
                            "release": bundle.Release
                        } for bundle in bundles
                    ]
                }
        elif product.Custom_ID:
            customs = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == product.Custom_ID,
                ProcedureCustom.Release == 1
            ).all()
            if customs:
                first_custom = customs[0]
                procedure_detail = {
                    "type": "custom",
                    "id": product.Custom_ID,
                    "name": first_custom.Name,
                    "description": f"커스텀 시술 (총 {len(customs)}개 Element 포함)",
                    "element_count": len(customs),
                    "customs": [
                        {
                            "id": custom.ID,
                            "element_id": custom.Element_ID,
                            "element_cost": custom.Element_Cost,
                            "custom_count": custom.Custom_Count,
                            "price_ratio": custom.Price_Ratio,
                            "release": custom.Release
                        } for custom in customs
                    ]
                }
        elif product.Sequence_ID:
            sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == product.Sequence_ID,
                ProcedureSequence.Release == 1
            ).order_by(ProcedureSequence.Step_Num).all()
            if sequences:
                first_sequence = sequences[0]
                procedure_detail = {
                    "type": "sequence",
                    "id": product.Sequence_ID,
                    "name": first_sequence.Name,
                    "description": f"시퀀스 시술 (총 {len(sequences)}개 Step 포함)",
                    "step_count": len(sequences),
                    "sequences": [
                        {
                            "id": sequence.ID,
                            "step_num": sequence.Step_Num,
                            "element_id": sequence.Element_ID,
                            "bundle_id": sequence.Bundle_ID,
                            "custom_id": sequence.Custom_ID,
                            "sequence_interval": sequence.Sequence_Interval,
                            "procedure_cost": sequence.Procedure_Cost,
                            "price_ratio": sequence.Price_Ratio,
                            "release": sequence.Release
                        } for sequence in sequences
                    ]
                }
        
        return {
            "status": "success",
            "message": "Standard Product 상세 조회 완료",
            "data": {
                "id": product.ID,
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": product.Standard_Start_Date,
                "end_date": product.Standard_End_Date,
                "validity_period": product.Validity_Period,
                "vat": product.VAT,
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
                "standard_info_id": product.Standard_Info_ID,
                "info_standard": info_standard,
                "procedure_info": procedure_info,
                "procedure_detail": procedure_detail
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standard Product 조회 중 오류가 발생했습니다: {str(e)}")

@products_router.get("/event/{product_id}", response_model=ProductDetailApiResponse)
async def get_event_product(product_id: int, db: Session = Depends(get_db)):
    """Event Product 상세 조회"""
    try:
        product = db.query(ProductEvent).filter(
            ProductEvent.ID == product_id,
            ProductEvent.Release == 1
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Event Product ID {product_id}를 찾을 수 없습니다.")
        
        # Info 정보 조회
        info_event = get_product_info(product, db)
        
        # Procedure 정보 조회
        procedure_info = get_procedure_info(product, db)
        
        # 연결된 시술 상세 정보 조회
        procedure_detail = None
        if product.Element_ID:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == product.Element_ID,
                ProcedureElement.Release == 1
            ).first()
            if element:
                procedure_detail = {
                    "type": "element",
                    "id": element.ID,
                    "name": element.Name,
                    "description": element.description,
                    "class_major": element.Class_Major,
                    "class_sub": element.Class_Sub,
                    "class_detail": element.Class_Detail,
                    "class_type": element.Class_Type,
                    "position_type": element.Position_Type,
                    "cost_time": element.Cost_Time,
                    "plan_state": element.Plan_State,
                    "plan_count": element.Plan_Count,
                    "plan_interval": element.Plan_Interval,
                    "consum_1_id": element.Consum_1_ID,
                    "consum_1_count": element.Consum_1_Count,
                    "procedure_level": element.Procedure_Level,
                    "procedure_cost": element.Procedure_Cost,
                    "price": element.Price,
                    "release": element.Release
                }
        elif product.Bundle_ID:
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == product.Bundle_ID,
                ProcedureBundle.Release == 1
            ).all()
            if bundles:
                first_bundle = bundles[0]
                procedure_detail = {
                    "type": "bundle",
                    "id": product.Bundle_ID,
                    "name": first_bundle.Name,
                    "description": f"번들 시술 (총 {len(bundles)}개 Element 포함)",
                    "element_count": len(bundles),
                    "bundles": [
                        {
                            "id": bundle.ID,
                            "element_id": bundle.Element_ID,
                            "element_cost": bundle.Element_Cost,
                            "price_ratio": bundle.Price_Ratio,
                            "release": bundle.Release
                        } for bundle in bundles
                    ]
                }
        elif product.Custom_ID:
            customs = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == product.Custom_ID,
                ProcedureCustom.Release == 1
            ).all()
            if customs:
                first_custom = customs[0]
                procedure_detail = {
                    "type": "custom",
                    "id": product.Custom_ID,
                    "name": first_custom.Name,
                    "description": f"커스텀 시술 (총 {len(customs)}개 Element 포함)",
                    "element_count": len(customs),
                    "customs": [
                        {
                            "id": custom.ID,
                            "element_id": custom.Element_ID,
                            "element_cost": custom.Element_Cost,
                            "custom_count": custom.Custom_Count,
                            "price_ratio": custom.Price_Ratio,
                            "release": custom.Release
                        } for custom in customs
                    ]
                }
        elif product.Sequence_ID:
            sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == product.Sequence_ID,
                ProcedureSequence.Release == 1
            ).order_by(ProcedureSequence.Step_Num).all()
            if sequences:
                first_sequence = sequences[0]
                procedure_detail = {
                    "type": "sequence",
                    "id": product.Sequence_ID,
                    "name": first_sequence.Name,
                    "description": f"시퀀스 시술 (총 {len(sequences)}개 Step 포함)",
                    "step_count": len(sequences),
                    "sequences": [
                        {
                            "id": sequence.ID,
                            "step_num": sequence.Step_Num,
                            "element_id": sequence.Element_ID,
                            "bundle_id": sequence.Bundle_ID,
                            "custom_id": sequence.Custom_ID,
                            "sequence_interval": sequence.Sequence_Interval,
                            "procedure_cost": sequence.Procedure_Cost,
                            "price_ratio": sequence.Price_Ratio,
                            "release": sequence.Release
                        } for sequence in sequences
                    ]
                }
        
        return {
            "status": "success",
            "message": "Event Product 상세 조회 완료",
            "data": {
                "id": product.ID,
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": product.Event_Start_Date,
                "end_date": product.Event_End_Date,
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
                "event_info_id": product.Event_Info_ID,
                "info_event": info_event,
                "procedure_info": procedure_info,
                "procedure_detail": procedure_detail
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event Product 조회 중 오류가 발생했습니다: {str(e)}")

@products_router.put("/standard/{product_id}")
async def update_standard_product(
    product_id: int,
    update_data: ProductUpdateRequest,
    db: Session = Depends(get_db)
):
    """Standard Product 수정 (모든 컬럼 수정 가능)"""
    try:
        updated_product = update_standard_product_full(product_id, update_data, db)
        
        try:
            db.commit()
        except IntegrityError as e:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"데이터 무결성 오류: {str(e)}")
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        
        # 수정된 Product의 상세 정보 조회 (ID가 변경된 경우 새로운 ID 사용)
        final_product_id = update_data.new_id if update_data.new_id else product_id
        product_detail = await get_standard_product_detail(final_product_id, db)
        
        return {
            "status": "success",
            "message": "Standard Product가 성공적으로 수정되었습니다.",
            "data": product_detail["data"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Standard Product 수정 중 오류가 발생했습니다: {str(e)}")

@products_router.put("/event/{product_id}")
async def update_event_product(
    product_id: int,
    update_data: ProductUpdateRequest,
    db: Session = Depends(get_db)
):
    """Event Product 수정 (모든 컬럼 수정 가능)"""
    try:
        print(f"=== Event Product 수정 시작 ===")
        print(f"Product ID: {product_id}")
        print(f"Update Data: {update_data}")
        
        updated_product = update_event_product_full(product_id, update_data, db)
        print(f"Updated Product: {updated_product.ID}")
        
        try:
            print("=== DB Commit 시도 ===")
            db.commit()
            print("=== DB Commit 성공 ===")
        except IntegrityError as e:
            print(f"=== DB Commit 실패 (IntegrityError): {str(e)} ===")
            db.rollback()
            raise HTTPException(status_code=400, detail=f"데이터 무결성 오류: {str(e)}")
        except SQLAlchemyError as e:
            print(f"=== DB Commit 실패 (SQLAlchemyError): {str(e)} ===")
            db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        
        # 수정된 Product의 상세 정보 조회 (ID가 변경된 경우 새로운 ID 사용)
        final_product_id = update_data.new_id if update_data.new_id else product_id
        print(f"Final Product ID: {final_product_id}")
        
        product_detail = await get_event_product_detail(final_product_id, db)
        print(f"Product Detail 조회 완료")
        
        return {
            "status": "success",
            "message": "Event Product가 성공적으로 수정되었습니다.",
            "data": product_detail["data"]
        }
        
    except HTTPException:
        print("=== HTTPException 발생 ===")
        raise
    except Exception as e:
        print(f"=== 일반 Exception 발생: {str(e)} ===")
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Event Product 수정 중 오류가 발생했습니다: {str(e)}")

@products_router.delete("/standard/{product_id}")
async def delete_standard_product(product_id: int, db: Session = Depends(get_db)):
    """Standard Product 삭제 (비활성화)"""
    try:
        product = db.query(ProductStandard).filter(
            ProductStandard.ID == product_id,
            ProductStandard.Release == 1
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Standard Product ID {product_id}를 찾을 수 없습니다.")
        
        # 비활성화 (실제 삭제 대신)
        product.Release = 0
        
        try:
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Standard Product ID {product_id}가 성공적으로 비활성화되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Standard Product 삭제 중 오류가 발생했습니다: {str(e)}")

@products_router.delete("/event/{product_id}")
async def delete_event_product(product_id: int, db: Session = Depends(get_db)):
    """Event Product 삭제 (비활성화)"""
    try:
        product = db.query(ProductEvent).filter(
            ProductEvent.ID == product_id,
            ProductEvent.Release == 1
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Event Product ID {product_id}를 찾을 수 없습니다.")
        
        # 비활성화 (실제 삭제 대신)
        product.Release = 0
        
        try:
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Event Product ID {product_id}가 성공적으로 비활성화되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Event Product 삭제 중 오류가 발생했습니다: {str(e)}")

@products_router.post("/standard/{product_id}/activate")
async def activate_standard_product(product_id: int, db: Session = Depends(get_db)):
    """Standard Product 활성화"""
    try:
        product = db.query(ProductStandard).filter(
            ProductStandard.ID == product_id,
            ProductStandard.Release == 0
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"비활성화된 Standard Product ID {product_id}를 찾을 수 없습니다.")
        
        # 활성화
        product.Release = 1
        
        try:
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Standard Product ID {product_id}가 성공적으로 활성화되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Standard Product 활성화 중 오류가 발생했습니다: {str(e)}")

@products_router.post("/event/{product_id}/activate")
async def activate_event_product(product_id: int, db: Session = Depends(get_db)):
    """Event Product 활성화"""
    try:
        product = db.query(ProductEvent).filter(
            ProductEvent.ID == product_id,
            ProductEvent.Release == 0
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"비활성화된 Event Product ID {product_id}를 찾을 수 없습니다.")
        
        # 활성화
        product.Release = 1
        
        try:
            db.commit()
        except SQLAlchemyError as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"데이터베이스 오류: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Event Product ID {product_id}가 성공적으로 활성화되었습니다."
        }
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Event Product 활성화 중 오류가 발생했습니다: {str(e)}")

# ============================================================================
# 핵심 로직 함수들
# ============================================================================

async def get_products_grouped_by_procedure(
    standard_query, event_query, db: Session
) -> dict:
    """시술별로 그룹화된 Product 목록 조회"""
    try:
        # 1. 시술별 Product 현황 조회
        procedure_products = {}
        
        # 모든 Product 조회 (페이지네이션 없음)
        standard_products = []
        event_products = []
        
        if standard_query is not None:
            standard_products = standard_query.all()
            print(f"DEBUG: Standard Products 조회 결과 - 개수: {len(standard_products)}")
            for product in standard_products:
                print(f"DEBUG: Standard Product - ID: {product.ID}, Release: {product.Release}, Package_Type: {product.Package_Type}")
        
        if event_query is not None:
            event_products = event_query.all()
            print(f"DEBUG: Event Products 조회 결과 - 개수: {len(event_products)}")
            for product in event_products:
                print(f"DEBUG: Event Product - ID: {product.ID}, Release: {product.Release}, Package_Type: {product.Package_Type}")
        
        # Standard Products 처리
        for product in standard_products:
            procedure_key = get_procedure_key(product)
            if procedure_key not in procedure_products:
                procedure_products[procedure_key] = {
                    "procedure_info": get_procedure_info(product, db),
                    "products": {"standard": [], "event": []}
                }
            procedure_products[procedure_key]["products"]["standard"].append({
                "id": product.ID,
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": product.Standard_Start_Date,
                "end_date": product.Standard_End_Date,
                "validity_period": product.Validity_Period,
                "vat": product.VAT,
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
                "standard_info_id": product.Standard_Info_ID,
                "info_standard": get_product_info(product, db)
            })
        
        # Event Products 처리
        print(f"=== Event Products 처리 시작 ===")
        for i, product in enumerate(event_products):
            try:
                print(f"Event Product {i+1} 처리 중: ID={product.ID}")
                procedure_key = get_procedure_key(product)
                print(f"  - procedure_key: {procedure_key}")
                
                if procedure_key not in procedure_products:
                    print(f"  - 새로운 procedure_key 추가: {procedure_key}")
                    procedure_products[procedure_key] = {
                        "procedure_info": get_procedure_info(product, db),
                        "products": {"standard": [], "event": []}
                    }
                
                print(f"  - Product 정보 추가 중...")
                procedure_products[procedure_key]["products"]["event"].append({
                    "id": product.ID,
                    "sell_price": product.Sell_Price,
                    "original_price": product.Original_Price,
                    "discount_rate": product.Discount_Rate,
                    "start_date": product.Event_Start_Date,
                    "end_date": product.Event_End_Date,
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
                    "event_info_id": product.Event_Info_ID,
                    "info_event": get_product_info(product, db)
                })
                print(f"  - Product 정보 추가 완료")
            except Exception as e:
                print(f"  - Event Product {i+1} 처리 중 에러: {str(e)}")
                print(f"  - 에러 상세: {type(e).__name__}")
                import traceback
                print(f"  - 스택 트레이스: {traceback.format_exc()}")
                raise
        
        # 2. 전체 데이터 반환
        procedure_list = list(procedure_products.values())
        
        return {
            "products": procedure_list
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시술별 Product 조회 중 오류가 발생했습니다: {str(e)}")

async def get_all_products(
    standard_query, event_query, db: Session
) -> dict:
    """전체 Product 목록 조회"""
    try:
        # 모든 Product 조회 (페이지네이션 없음)
        print(f"=== get_all_products 디버깅 ===")
        print(f"standard_query: {standard_query}")
        print(f"event_query: {event_query}")
        
        standard_products = []
        event_products = []
        standard_data = []
        event_data = []
        
        # 1. Standard Products 조회
        if standard_query is not None:
            standard_products = standard_query.all()
            print(f"Standard Products 조회 결과: {len(standard_products)}개")
            
            for product in standard_products:
                standard_data.append({
                "id": product.ID,
                "type": "standard",
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": product.Standard_Start_Date,
                "end_date": product.Standard_End_Date,
                "validity_period": product.Validity_Period,
                "vat": product.VAT,
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
                "standard_info_id": product.Standard_Info_ID,
                "info_standard": get_product_info(product, db)
            })
        
        # 2. Event Products 조회
        if event_query is not None:
            event_products = event_query.all()
            print(f"Event Products 조회 결과: {len(event_products)}개")
            
            for product in event_products:
                event_data.append({
                "id": product.ID,
                "type": "event",
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": product.Event_Start_Date,
                "end_date": product.Event_End_Date,
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
                "event_info_id": product.Event_Info_ID,
                "info_event": get_product_info(product, db)
            })
        
        # 3. 전체 데이터 합치기
        all_products = standard_data + event_data
        print(f"전체 Products 합계: {len(all_products)}개")
        return {
            "products": all_products
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"전체 Product 조회 중 오류가 발생했습니다: {str(e)}")

def get_procedure_key(product) -> str:
    """Product의 시술 키 생성"""
    if hasattr(product, 'Element_ID') and product.Element_ID:
        return f"element_{product.Element_ID}"
    elif hasattr(product, 'Bundle_ID') and product.Bundle_ID:
        return f"bundle_{product.Bundle_ID}"
    elif hasattr(product, 'Custom_ID') and product.Custom_ID:
        return f"custom_{product.Custom_ID}"
    elif hasattr(product, 'Sequence_ID') and product.Sequence_ID:
        return f"sequence_{product.Sequence_ID}"
    else:
        return "unknown"

def get_product_info(product, db: Session) -> dict:
    """Product의 Info 정보 조회 (목록 조회용)"""
    try:
        if hasattr(product, 'Standard_Info_ID') and product.Standard_Info_ID:
            # Standard Info 조회
            info = db.query(InfoStandard).filter(
                InfoStandard.ID == product.Standard_Info_ID
            ).first()
            
            if info:
                return {
                    "type": "standard",
                    "id": info.ID,
                    "name": info.Product_Standard_Name,
                    "description": info.Product_Standard_Description,
                    "precautions": info.Precautions
                }
            else:
                return {"type": "standard", "id": product.Standard_Info_ID, "name": "Unknown", "description": "Unknown", "precautions": None}
                
        elif hasattr(product, 'Event_Info_ID') and product.Event_Info_ID:
            # Event Info 조회
            info = db.query(InfoEvent).filter(
                InfoEvent.ID == product.Event_Info_ID
            ).first()
            
            if info:
                return {
                    "type": "event",
                    "id": info.ID,
                    "name": info.Event_Name,
                    "description": info.Event_Description,
                    "precautions": info.Precautions
                }
            else:
                return {"type": "event", "id": product.Event_Info_ID, "name": "Unknown", "description": "Unknown", "precautions": None}
        else:
            return {"type": "unknown", "id": 0, "name": "Unknown", "description": "Unknown", "precautions": None}
    except:
        return {"type": "unknown", "id": 0, "name": "Unknown", "description": "Unknown", "precautions": None}

def get_element_detail_with_consumable(element_id: int, db: Session) -> dict:
    """Element의 상세 정보와 소모품 정보를 함께 조회"""
    try:
        element = db.query(ProcedureElement).filter(
            ProcedureElement.ID == element_id,
            ProcedureElement.Release == 1
        ).first()
        
        if not element:
            return None
        
        # 소모품 정보 조회
        consumable_info = get_consumable_info(element.Consum_1_ID, db)
        
        return {
            "id": element.ID,
            "name": element.Name,
            "description": element.description,
            "class_major": element.Class_Major,
            "class_sub": element.Class_Sub,
            "class_detail": element.Class_Detail,
            "class_type": element.Class_Type,
            "position_type": element.Position_Type,
            "cost_time": element.Cost_Time,
            "plan_state": element.Plan_State,
            "plan_count": element.Plan_Count,
            "plan_interval": element.Plan_Interval,
            "consum_1_id": element.Consum_1_ID,
            "consum_1_count": element.Consum_1_Count,
            "procedure_level": element.Procedure_Level,
            "procedure_cost": element.Procedure_Cost,
            "price": element.Price,
            "consumable_info": consumable_info
        }
    except Exception as e:
        print(f"DEBUG: Error getting element detail: {str(e)}")
        return None

def get_procedure_detail_enhanced(product, db: Session) -> dict:
    """Product의 시술 상세 정보 조회 (Enhanced with element details)"""
    try:
        if product.Element_ID:
            element_detail = get_element_detail_with_consumable(product.Element_ID, db)
            if element_detail:
                return {
                    "type": "element",
                    "id": element_detail["id"],
                    "name": element_detail["name"],
                    "description": element_detail["description"],
                    "element_detail": element_detail
                }
        
        elif product.Bundle_ID:
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == product.Bundle_ID,
                ProcedureBundle.Release == 1
            ).all()
            if bundles:
                first_bundle = bundles[0]
                
                # 번들에 포함된 모든 Element들의 상세 정보 조회
                bundle_elements = []
                for bundle in bundles:
                    element_detail = get_element_detail_with_consumable(bundle.Element_ID, db)
                    if element_detail:
                        # 번들 관련 정보 추가
                        element_detail["bundle_element_cost"] = bundle.Element_Cost
                        element_detail["price_ratio"] = bundle.Price_Ratio
                        bundle_elements.append(element_detail)
                
                return {
                    "type": "bundle",
                    "id": product.Bundle_ID,
                    "name": first_bundle.Name,
                    "description": f"번들 시술 (총 {len(bundles)}개 Element 포함)",
                    "element_count": len(bundles),
                    "bundles": [
                        {
                            "id": bundle.ID,
                            "element_id": bundle.Element_ID,
                            "element_cost": bundle.Element_Cost,
                            "price_ratio": bundle.Price_Ratio,
                            "release": bundle.Release
                        } for bundle in bundles
                    ],
                    "elements_detail": bundle_elements  # 모든 Element의 상세 정보
                }
        
        elif product.Custom_ID:
            customs = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == product.Custom_ID,
                ProcedureCustom.Release == 1
            ).all()
            if customs:
                first_custom = customs[0]
                
                # 커스텀에 포함된 모든 Element들의 상세 정보 조회
                custom_elements = []
                for custom in customs:
                    element_detail = get_element_detail_with_consumable(custom.Element_ID, db)
                    if element_detail:
                        # 커스텀 관련 정보 추가
                        element_detail["custom_element_cost"] = custom.Element_Cost
                        element_detail["custom_count"] = custom.Custom_Count
                        element_detail["price_ratio"] = custom.Price_Ratio
                        custom_elements.append(element_detail)
                
                return {
                    "type": "custom",
                    "id": product.Custom_ID,
                    "name": first_custom.Name,
                    "description": f"커스텀 시술 (총 {len(customs)}개 Element 포함)",
                    "element_count": len(customs),
                    "customs": [
                        {
                            "id": custom.ID,
                            "element_id": custom.Element_ID,
                            "element_cost": custom.Element_Cost,
                            "custom_count": custom.Custom_Count,
                            "price_ratio": custom.Price_Ratio,
                            "release": custom.Release
                        } for custom in customs
                    ],
                    "elements_detail": custom_elements  # 모든 Element의 상세 정보
                }
        
        elif product.Sequence_ID:
            sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == product.Sequence_ID,
                ProcedureSequence.Release == 1
            ).order_by(ProcedureSequence.Step_Num).all()
            if sequences:
                first_sequence = sequences[0]
                
                # 시퀀스의 각 스텝별 상세 정보 조회
                detailed_steps = []
                all_elements = []
                
                for sequence in sequences:
                    step_info = {
                        "id": sequence.ID,
                        "step_num": sequence.Step_Num,
                        "element_id": sequence.Element_ID,
                        "bundle_id": sequence.Bundle_ID,
                        "custom_id": sequence.Custom_ID,
                        "sequence_interval": sequence.Sequence_Interval,
                        "procedure_cost": sequence.Procedure_Cost,
                        "price_ratio": sequence.Price_Ratio,
                        "release": sequence.Release
                    }
                    
                    # Element 참조인 경우
                    if sequence.Element_ID:
                        element_detail = get_element_detail_with_consumable(sequence.Element_ID, db)
                        if element_detail:
                            step_info["element_detail"] = element_detail
                            all_elements.append(element_detail)
                    
                    # Bundle 참조인 경우
                    elif sequence.Bundle_ID:
                        bundles_in_seq = db.query(ProcedureBundle).filter(
                            ProcedureBundle.GroupID == sequence.Bundle_ID,
                            ProcedureBundle.Release == 1
                        ).all()
                        if bundles_in_seq:
                            bundle_elements_in_seq = []
                            for bundle in bundles_in_seq:
                                element_detail = get_element_detail_with_consumable(bundle.Element_ID, db)
                                if element_detail:
                                    element_detail["bundle_element_cost"] = bundle.Element_Cost
                                    element_detail["price_ratio"] = bundle.Price_Ratio
                                    bundle_elements_in_seq.append(element_detail)
                                    all_elements.append(element_detail)
                            
                            step_info["bundle_detail"] = {
                                "id": sequence.Bundle_ID,
                                "name": bundles_in_seq[0].Name,
                                "element_count": len(bundles_in_seq),
                                "elements": bundle_elements_in_seq
                            }
                    
                    # Custom 참조인 경우
                    elif sequence.Custom_ID:
                        customs_in_seq = db.query(ProcedureCustom).filter(
                            ProcedureCustom.GroupID == sequence.Custom_ID,
                            ProcedureCustom.Release == 1
                        ).all()
                        if customs_in_seq:
                            custom_elements_in_seq = []
                            for custom in customs_in_seq:
                                element_detail = get_element_detail_with_consumable(custom.Element_ID, db)
                                if element_detail:
                                    element_detail["custom_element_cost"] = custom.Element_Cost
                                    element_detail["custom_count"] = custom.Custom_Count
                                    element_detail["price_ratio"] = custom.Price_Ratio
                                    custom_elements_in_seq.append(element_detail)
                                    all_elements.append(element_detail)
                            
                            step_info["custom_detail"] = {
                                "id": sequence.Custom_ID,
                                "name": customs_in_seq[0].Name,
                                "element_count": len(customs_in_seq),
                                "elements": custom_elements_in_seq
                            }
                    
                    detailed_steps.append(step_info)
                
                return {
                    "type": "sequence",
                    "id": product.Sequence_ID,
                    "name": first_sequence.Name if hasattr(first_sequence, 'Name') and first_sequence.Name else f"시퀀스 {product.Sequence_ID}",
                    "description": f"시퀀스 시술 (총 {len(sequences)}개 Step 포함)",
                    "step_count": len(sequences),
                    "sequences": detailed_steps,
                    "all_elements_detail": all_elements  # 시퀀스에 포함된 모든 Element의 상세 정보
                }
        
        return None
        
    except Exception as e:
        print(f"DEBUG: Error in get_procedure_detail_enhanced: {str(e)}")
        return None

def get_consumable_info(consumable_id: int, db: Session) -> dict:
    """소모품 정보 조회"""
    try:
        if not consumable_id:
            return None
        
        consumable = db.query(Consumables).filter(
            Consumables.ID == consumable_id,
            Consumables.Release == 1
        ).first()
        
        if not consumable:
            return None
        
        return {
            "id": consumable.ID,
            "name": consumable.Name,
            "description": consumable.Description,
            "unit_type": consumable.Unit_Type,
            "i_value": consumable.I_Value,
            "f_value": consumable.F_Value,
            "price": consumable.Price,
            "unit_price": consumable.Unit_Price,
            "vat": consumable.VAT,
            "taxable_type": consumable.TaxableType,
            "covered_type": consumable.Covered_Type
        }
    except Exception as e:
        return None

def get_procedure_info(product, db: Session) -> dict:
    """Product의 시술 정보 조회 (상세 조회용)"""
    try:
        
        if hasattr(product, 'Element_ID') and product.Element_ID is not None:
            print(f"DEBUG: Processing Element_ID: {product.Element_ID}")
            return validate_procedure_reference_simple("단일시술", element_id=product.Element_ID, db=db)
        elif hasattr(product, 'Bundle_ID') and product.Bundle_ID is not None:
            print(f"DEBUG: Processing Bundle_ID: {product.Bundle_ID}")
            try:
                result = validate_procedure_reference_simple("번들", bundle_id=product.Bundle_ID, db=db)
                print(f"DEBUG: Bundle 처리 결과: {result}")
                return result
            except Exception as e:
                print(f"DEBUG: Bundle 처리 중 에러: {str(e)}")
                return {"type": "bundle", "id": product.Bundle_ID, "name": "Error", "description": f"Error: {str(e)}"}
        elif hasattr(product, 'Custom_ID') and product.Custom_ID is not None:
            print(f"DEBUG: Processing Custom_ID: {product.Custom_ID}")
            return validate_procedure_reference_simple("커스텀", custom_id=product.Custom_ID, db=db)
        elif hasattr(product, 'Sequence_ID') and product.Sequence_ID is not None:
            print(f"DEBUG: Processing Sequence_ID: {product.Sequence_ID}")
            return validate_procedure_reference_simple("시퀀스", sequence_id=product.Sequence_ID, db=db)
        else:
            print("DEBUG: No procedure reference found")
            return {"type": "unknown", "id": 0, "name": "Unknown", "description": "Unknown"}
    except Exception as e:
        print(f"DEBUG: Error in get_procedure_info: {str(e)}")
        return {"type": "unknown", "id": 0, "name": "Unknown", "description": f"Error: {str(e)}"}

def validate_procedure_reference_simple(
    package_type: str,
    element_id: Optional[int] = None,
    bundle_id: Optional[int] = None,
    custom_id: Optional[int] = None,
    sequence_id: Optional[int] = None,
    db: Session = None
) -> dict:
    """
    시술 참조 검증 및 정보 조회 (Release 상태와 관계없이)
    
    Args:
        package_type: 시술 타입 ("단일시술", "번들", "커스텀", "시퀀스")
        element_id, bundle_id, custom_id, sequence_id: 참조할 시술 ID
        db: 데이터베이스 세션
    
    Returns:
        dict: 시술 정보 (name, description, procedure_cost 등)
    """
    try:
        if package_type == "단일시술":
            if element_id is None:
                return {"type": "element", "id": 0, "name": "Unknown", "description": "Element ID가 필요합니다."}
            
            # Release 상태와 관계없이 조회
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == element_id
            ).first()
            
            if not element:
                return {"type": "element", "id": element_id, "name": "Unknown", "description": f"Element ID {element_id}를 찾을 수 없습니다."}
            
            # 소모품 정보 조회
            consumable_info = get_consumable_info(element.Consum_1_ID, db)
            
            return {
                "type": "element",
                "id": element.ID,
                "name": element.Name,
                "description": element.description,
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
                "consumable_info": consumable_info,
                "procedure_level": element.Procedure_Level,
                "price": element.Price
            }
            
        elif package_type == "번들":
            if bundle_id is None:
                print(f"DEBUG: Bundle ID가 None")
                return {"type": "bundle", "id": 0, "name": "Unknown", "description": "Bundle ID가 필요합니다."}
            
            print(f"DEBUG: 번들 처리 시작 - bundle_id: {bundle_id}")
            
            # Release 상태와 관계없이 조회
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == bundle_id
            ).all()
            
            print(f"DEBUG: 번들 조회 결과 - 개수: {len(bundles) if bundles else 0}")
            
            if not bundles:
                print(f"DEBUG: 번들을 찾을 수 없음 - GroupID: {bundle_id}")
                return {"type": "bundle", "id": bundle_id, "name": "Unknown", "description": f"Bundle GroupID {bundle_id}를 찾을 수 없습니다."}
            
            print(f"DEBUG: 번들 처리 계속 - 첫 번째 번들: {bundles[0].ID if bundles else 'None'}")
            
            # 첫 번째 번들의 정보 사용
            first_bundle = bundles[0]
            
            # 번들에 포함된 Element들의 총 비용 계산
            total_cost = sum(bundle.Element_Cost for bundle in bundles)
            
            return {
                "type": "bundle",
                "id": bundle_id,
                "name": first_bundle.Name,
                "description": f"번들 시술 (총 {len(bundles)}개 Element 포함)",
                "procedure_cost": total_cost,
                "element_count": len(bundles)
            }
            
        elif package_type == "커스텀":
            if custom_id is None:
                return {"type": "custom", "id": 0, "name": "Unknown", "description": "Custom ID가 필요합니다."}
            
            # Release 상태와 관계없이 조회
            customs = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == custom_id
            ).all()
            
            if not customs:
                return {"type": "custom", "id": custom_id, "name": "Unknown", "description": f"Custom GroupID {custom_id}를 찾을 수 없습니다."}
            
            # 첫 번째 커스텀의 정보 사용
            first_custom = customs[0]
            
            # 커스텀에 포함된 Element들의 총 비용 계산
            total_cost = sum(custom.Element_Cost for custom in customs)
            
            return {
                "type": "custom",
                "id": custom_id,
                "name": first_custom.Name,
                "description": f"커스텀 시술 (총 {len(customs)}개 Element 포함)",
                "procedure_cost": total_cost,
                "element_count": len(customs)
            }
            
        elif package_type == "시퀀스":
            if sequence_id is None:
                return {"type": "sequence", "id": 0, "name": "Unknown", "description": "Sequence ID가 필요합니다."}
            
            print(f"DEBUG: 시퀀스 처리 시작 - sequence_id: {sequence_id}")
            
            # Sequence GroupID로 조회
            sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == sequence_id,
                ProcedureSequence.Release == 1
            ).order_by(ProcedureSequence.Step_Num).all()
            
            print(f"DEBUG: 시퀀스 조회 결과 - 개수: {len(sequences) if sequences else 0}")
            
            if not sequences:
                print(f"DEBUG: 시퀀스를 찾을 수 없음 - GroupID: {sequence_id}")
                raise HTTPException(status_code=404, detail=f"Sequence GroupID {sequence_id}를 찾을 수 없거나 비활성화되어 있습니다.")
            
            print(f"DEBUG: 시퀀스 처리 계속 - 첫 번째 시퀀스: {sequences[0].ID if sequences else 'None'}")
            
            # 첫 번째 시퀀스의 정보 사용
            first_sequence = sequences[0]
            
            return {
                "type": "sequence",
                "id": sequence_id,
                "name": first_sequence.Name,
                "description": f"시퀀스 시술 (총 {len(sequences)}개 Element 포함)",
                "procedure_cost": 0,  # 시퀀스는 개별 비용을 가짐
                "element_count": len(sequences)
            }
            
            print(f"DEBUG: 시퀀스 처리 완료 - type: sequence, id: {sequence_id}")
        
        else:
            return {"type": "unknown", "id": 0, "name": "Unknown", "description": f"알 수 없는 시술 타입: {package_type}"}
            
    except Exception as e:
        print(f"DEBUG: Error in validate_procedure_reference_simple: {str(e)}")
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
            
            # 소모품 정보 조회
            consumable_info = get_consumable_info(element.Consum_1_ID, db)
            
            return {
                "type": "element",
                "id": element.ID,
                "name": element.Name,
                "description": element.description,
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
                "consumable_info": consumable_info,
                "procedure_level": element.Procedure_Level,
                "price": element.Price
            }
            
        elif package_type == "번들":
            if bundle_id is None:
                raise HTTPException(status_code=400, detail="Bundle ID가 필요합니다.")
            
            # Bundle GroupID로 조회
            bundles = db.query(ProcedureBundle).filter(
                ProcedureBundle.GroupID == bundle_id,
                ProcedureBundle.Release == 1
            ).all()
            
            if not bundles:
                raise HTTPException(status_code=404, detail=f"Bundle GroupID {bundle_id}를 찾을 수 없거나 비활성화되어 있습니다.")
            
            # 첫 번째 번들의 정보 사용 (모든 번들이 같은 GroupID를 가짐)
            first_bundle = bundles[0]
            
            # 번들에 포함된 Element들의 총 비용 계산
            total_cost = sum(bundle.Element_Cost for bundle in bundles)
            
            # Element 정보 조회
            element_ids = [bundle.Element_ID for bundle in bundles]
            elements = db.query(ProcedureElement).filter(
                ProcedureElement.ID.in_(element_ids),
                ProcedureElement.Release == 1
            ).all()
            element_dict = {element.ID: element for element in elements}
            
            detailed_elements = []
            for bundle in bundles:
                element = element_dict.get(bundle.Element_ID)
                if element:
                    # 소모품 정보 조회
                    consumable_info = get_consumable_info(element.Consum_1_ID, db)
                    
                    element_detail = {
                        "element_id": bundle.Element_ID,
                        "element_name": element.Name,
                        "element_cost": bundle.Element_Cost,
                        "price_ratio": bundle.Price_Ratio,
                        "description": element.description,
                        "class_major": element.Class_Major,
                        "class_sub": element.Class_Sub,
                        "class_detail": element.Class_Detail,
                        "class_type": element.Class_Type,
                        "position_type": element.Position_Type,
                        "cost_time": element.Cost_Time,
                        "plan_state": element.Plan_State,
                        "plan_count": element.Plan_Count,
                        "plan_interval": element.Plan_Interval,
                        "consum_1_id": element.Consum_1_ID,
                        "consum_1_count": element.Consum_1_Count,
                        "consumable_info": consumable_info,
                        "procedure_level": element.Procedure_Level,
                        "procedure_cost": element.Procedure_Cost,
                        "price": element.Price
                    }
                    detailed_elements.append(element_detail)
            
            return {
                "type": "bundle",
                "id": bundle_id,
                "name": first_bundle.Name,
                "description": f"번들 시술 (총 {len(bundles)}개 Element 포함)",
                "procedure_cost": total_cost,
                "element_count": len(bundles),
                "elements": detailed_elements
            }
            
        elif package_type == "커스텀":
            if custom_id is None:
                raise HTTPException(status_code=400, detail="Custom ID가 필요합니다.")
            
            # Custom GroupID로 조회
            customs = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == custom_id,
                ProcedureCustom.Release == 1
            ).all()
            
            if not customs:
                raise HTTPException(status_code=404, detail=f"Custom GroupID {custom_id}를 찾을 수 없거나 비활성화되어 있습니다.")
            
            # 첫 번째 커스텀의 정보 사용
            first_custom = customs[0]
            
            # 커스텀에 포함된 Element들의 총 비용 계산
            total_cost = sum(custom.Element_Cost for custom in customs)
            
            # Element 정보 조회
            element_ids = [custom.Element_ID for custom in customs]
            elements = db.query(ProcedureElement).filter(
                ProcedureElement.ID.in_(element_ids),
                ProcedureElement.Release == 1
            ).all()
            element_dict = {element.ID: element for element in elements}
            
            detailed_elements = []
            for custom in customs:
                element = element_dict.get(custom.Element_ID)
                if element:
                    # 소모품 정보 조회
                    consumable_info = get_consumable_info(element.Consum_1_ID, db)
                    
                    element_detail = {
                        "element_id": custom.Element_ID,
                        "element_name": element.Name,
                        "element_cost": custom.Element_Cost,
                        "custom_count": custom.Custom_Count,
                        "price_ratio": custom.Price_Ratio,
                        "description": element.description,
                        "class_major": element.Class_Major,
                        "class_sub": element.Class_Sub,
                        "class_detail": element.Class_Detail,
                        "class_type": element.Class_Type,
                        "position_type": element.Position_Type,
                        "cost_time": element.Cost_Time,
                        "plan_state": element.Plan_State,
                        "plan_count": element.Plan_Count,
                        "plan_interval": element.Plan_Interval,
                        "consum_1_id": element.Consum_1_ID,
                        "consum_1_count": element.Consum_1_Count,
                        "consumable_info": consumable_info,
                        "procedure_level": element.Procedure_Level,
                        "procedure_cost": element.Procedure_Cost,
                        "price": element.Price
                    }
                    detailed_elements.append(element_detail)
            
            return {
                "type": "custom",
                "id": custom_id,
                "name": first_custom.Name,
                "description": f"커스텀 시술 (총 {len(customs)}개 Element 포함)",
                "procedure_cost": total_cost,
                "element_count": len(customs),
                "elements": detailed_elements
            }
            
        elif package_type == "시퀀스":
            if sequence_id is None:
                raise HTTPException(status_code=400, detail="Sequence ID가 필요합니다.")
            
            print(f"DEBUG: 시퀀스 처리 시작 - sequence_id: {sequence_id}")
            
            # Sequence GroupID로 조회
            sequences = db.query(ProcedureSequence).filter(
                ProcedureSequence.GroupID == sequence_id,
                ProcedureSequence.Release == 1
            ).order_by(ProcedureSequence.Step_Num).all()
            
            print(f"DEBUG: 시퀀스 조회 결과 - 개수: {len(sequences) if sequences else 0}")
            
            if not sequences:
                print(f"DEBUG: 시퀀스를 찾을 수 없음 - GroupID: {sequence_id}")
                raise HTTPException(status_code=404, detail=f"Sequence GroupID {sequence_id}를 찾을 수 없거나 비활성화되어 있습니다.")
            
            print(f"DEBUG: 시퀀스 처리 계속 - 첫 번째 시퀀스: {sequences[0].ID if sequences else 'None'}")
            
            # 첫 번째 시퀀스의 정보 사용
            first_sequence = sequences[0]
            
            return {
                "type": "sequence",
                "id": sequence_id,
                "name": first_sequence.Name,
                "description": f"시퀀스 시술 (총 {len(sequences)}개 Element 포함)",
                "procedure_cost": 0,  # 시퀀스는 개별 비용을 가짐
                "element_count": len(sequences)
            }
            
            print(f"DEBUG: 시퀀스 처리 완료 - type: sequence, id: {sequence_id}")
        
        else:
            raise HTTPException(status_code=400, detail=f"지원하지 않는 시술 타입입니다: {package_type}")
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"시술 참조 검증 중 오류가 발생했습니다: {str(e)}")

def calculate_product_margin(sell_price: int, procedure_cost: int) -> dict:
    """
    Product 마진 계산
    
    Args:
        sell_price: 판매가
        procedure_cost: 시술 비용
    
    Returns:
        dict: 계산된 마진 정보
    """
    try:
        margin = sell_price - procedure_cost
        margin_rate = (margin / sell_price * 100) if sell_price > 0 else 0
        
        return {
            "sell_price": sell_price,
            "procedure_cost": procedure_cost,
            "margin": margin,
            "margin_rate": round(margin_rate, 2)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"마진 계산 중 오류가 발생했습니다: {str(e)}")

def create_standard_product(
    procedure_info: dict,
    settings: StandardSettingsRequest,
    db: Session
) -> ProductStandard:
    """
    Standard Product 생성
    
    Args:
        procedure_info: 시술 정보
        settings: Standard 설정
        db: 데이터베이스 세션
    
    Returns:
        ProductStandard: 생성된 Standard Product
    """
    try:
        # 시술 참조 정보 설정
        if procedure_info["type"] == "element":
            element_id = procedure_info.get("element_id")
            bundle_id = None
            custom_id = None
            sequence_id = None
        elif procedure_info["type"] == "bundle":
            element_id = None
            bundle_id = procedure_info.get("bundle_id")
            custom_id = None
            sequence_id = None
        elif procedure_info["type"] == "custom":
            element_id = None
            bundle_id = None
            custom_id = procedure_info.get("custom_id")
            sequence_id = None
        elif procedure_info["type"] == "sequence":
            element_id = None
            bundle_id = None
            custom_id = None
            sequence_id = procedure_info.get("sequence_id")
        
        # 마진 계산 (설정에서 제공된 값이 있으면 사용, 없으면 계산)
        if settings.margin is not None and settings.margin_rate is not None:
            margin = settings.margin
            margin_rate = settings.margin_rate
        else:
            margin_info = calculate_product_margin(settings.sell_price, settings.procedure_cost or procedure_info["procedure_cost"])
            margin = margin_info["margin"]
            margin_rate = margin_info["margin_rate"]
        
        # 기본 날짜 설정 (날짜가 없을 경우)
        from datetime import datetime, timedelta
        today = datetime.now()
        default_start_date = today.strftime("%Y-%m-%d")
        default_end_date = (today + timedelta(days=60)).strftime("%Y-%m-%d")  # 2개월 후
        
        # ProductStandard 생성
        product_id = procedure_info.get("id") if procedure_info.get("id") is not None else get_next_product_id("standard", db)
        print(f"DEBUG: ProductStandard ID 설정 - procedure_info.get('id'): {procedure_info.get('id')}, 최종 ID: {product_id}")
        
        product = ProductStandard(
            ID=product_id,
            Release=procedure_info.get("release", 1),
            Package_Type=procedure_info.get("package_type"),
            Element_ID=element_id,
            Bundle_ID=bundle_id,
            Custom_ID=custom_id,
            Sequence_ID=sequence_id,
            Standard_Info_ID=settings.standard_info_id,
            Sell_Price=settings.sell_price,
            Original_Price=settings.original_price or settings.sell_price,
            Discount_Rate=settings.discount_rate or 0,
            Standard_Start_Date=settings.start_date or default_start_date,
            Standard_End_Date=settings.end_date or default_end_date,
            Covered_Type=settings.covered_type,
            Taxable_Type=settings.taxable_type,
            Procedure_Cost=settings.procedure_cost or procedure_info["procedure_cost"],
            Margin=margin,
            Margin_Rate=margin_rate,
            VAT=settings.vat,
            Validity_Period=settings.validity_period,
            Procedure_Grade=procedure_info.get("procedure_grade")
        )
        
        db.add(product)
        db.flush()  # ID 생성을 위해 flush
        print(f"DEBUG: ProductStandard 생성 완료 - ID: {product.ID}")
        
        # Info_Standard 생성 (설정에서 info 관련 필드가 제공된 경우)
        if (settings.product_standard_name or settings.product_standard_description or settings.precautions):
            try:
                # 기존 standard_info_id가 있으면 사용, 없으면 새로 생성
                if settings.standard_info_id:
                    print(f"DEBUG: 기존 Info_Standard 사용 시도 - ID: {settings.standard_info_id}")
                    # 기존 info가 실제로 존재하는지 확인
                    existing_info = db.query(InfoStandard).filter(InfoStandard.ID == settings.standard_info_id).first()
                    if existing_info:
                        print(f"DEBUG: 기존 Info_Standard 존재 확인 - ID: {settings.standard_info_id}")
                        # ProductStandard의 Standard_Info_ID 설정
                        product.Standard_Info_ID = settings.standard_info_id
                        print(f"DEBUG: ProductStandard.Standard_Info_ID 설정됨: {product.Standard_Info_ID}")
                    else:
                        print(f"DEBUG: 기존 Info_Standard가 존재하지 않음 - ID: {settings.standard_info_id}, 새로운 info 생성")
                        info_standard = create_info_standard(product.ID, settings, db)
                        # ProductStandard의 Standard_Info_ID 업데이트
                        product.Standard_Info_ID = info_standard.ID
                        print(f"DEBUG: 새로운 Info_Standard 생성 완료 - ID: {info_standard.ID}")
                else:
                    info_standard = create_info_standard(product.ID, settings, db)
                    # ProductStandard의 Standard_Info_ID 업데이트
                    product.Standard_Info_ID = info_standard.ID
                    print(f"DEBUG: 새로운 Info_Standard 생성 완료 - ID: {info_standard.ID}")
            except Exception as e:
                print(f"DEBUG: Info_Standard 생성 실패: {str(e)}")
                raise e
        else:
            # info 관련 필드가 없어도 standard_info_id가 있으면 설정
            if settings.standard_info_id:
                print(f"DEBUG: Info 관련 필드 없음, 기존 standard_info_id 사용 시도: {settings.standard_info_id}")
                # 기존 info가 실제로 존재하는지 확인
                existing_info = db.query(InfoStandard).filter(InfoStandard.ID == settings.standard_info_id).first()
                if existing_info:
                    print(f"DEBUG: 기존 Info_Standard 존재 확인 - ID: {settings.standard_info_id}")
                    product.Standard_Info_ID = settings.standard_info_id
                    print(f"DEBUG: ProductStandard.Standard_Info_ID 설정됨: {product.Standard_Info_ID}")
                else:
                    print(f"DEBUG: 기존 Info_Standard가 존재하지 않음 - ID: {settings.standard_info_id}")
                    # 기본 info 생성
                    info_standard = create_info_standard(product.ID, settings, db)
                    product.Standard_Info_ID = info_standard.ID
                    print(f"DEBUG: 기본 Info_Standard 생성 완료 - ID: {info_standard.ID}")
            else:
                print(f"DEBUG: Info 관련 필드도 없고, standard_info_id도 없음")
        
        return product
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standard Product 생성 중 오류가 발생했습니다: {str(e)}")

def create_event_product(
    procedure_info: dict,
    settings: EventSettingsRequest,
    db: Session
) -> ProductEvent:
    """
    Event Product 생성
    
    Args:
        procedure_info: 시술 정보
        settings: Event 설정
        db: 데이터베이스 세션
    
    Returns:
        ProductEvent: 생성된 Event Product
    """
    try:
        # 시술 참조 정보 설정
        if procedure_info["type"] == "element":
            element_id = procedure_info.get("element_id")
            bundle_id = None
            custom_id = None
            sequence_id = None
        elif procedure_info["type"] == "bundle":
            element_id = None
            bundle_id = procedure_info.get("bundle_id")
            custom_id = None
            sequence_id = None
        elif procedure_info["type"] == "custom":
            element_id = None
            bundle_id = None
            custom_id = procedure_info.get("custom_id")
            sequence_id = None
        elif procedure_info["type"] == "sequence":
            element_id = None
            bundle_id = None
            custom_id = None
            sequence_id = procedure_info.get("sequence_id")
        
        # 할인가 계산 (설정에서 제공된 값이 있으면 사용, 없으면 계산)
        if settings.original_price is not None and settings.discount_rate is not None:
            original_price = settings.original_price
            discount_rate = settings.discount_rate
            discounted_price = int(original_price * (1 - discount_rate / 100))
        else:
            discount_rate = settings.discount_rate or 0
            original_price = settings.sell_price
            discounted_price = int(original_price * (1 - discount_rate / 100))
        
        # 마진 계산 (설정에서 제공된 값이 있으면 사용, 없으면 계산)
        if settings.margin is not None and settings.margin_rate is not None:
            margin = settings.margin
            margin_rate = settings.margin_rate
        else:
            margin_info = calculate_product_margin(discounted_price, settings.procedure_cost or procedure_info["procedure_cost"])
            margin = margin_info["margin"]
            margin_rate = margin_info["margin_rate"]
        
        # 기본 날짜 설정 (날짜가 없을 경우)
        today = datetime.now()
        default_start_date = today.strftime("%Y-%m-%d")
        default_end_date = (today + timedelta(days=60)).strftime("%Y-%m-%d")  # 2개월 후
        
        # ProductEvent 생성
        product_id = procedure_info.get("id") if procedure_info.get("id") is not None else get_next_product_id("event", db)
        print(f"DEBUG: ProductEvent ID 설정 - procedure_info.get('id'): {procedure_info.get('id')}, 최종 ID: {product_id}")
        
        product = ProductEvent(
            ID=product_id,
            Release=procedure_info.get("release", 1),
            Package_Type=procedure_info.get("package_type"),  # Package_Type 추가
            Element_ID=element_id,
            Bundle_ID=bundle_id,
            Custom_ID=custom_id,
            Sequence_ID=sequence_id,
            Event_Info_ID=settings.event_info_id,
            Sell_Price=discounted_price,
            Original_Price=original_price,
            Discount_Rate=discount_rate,
            Event_Start_Date=settings.start_date or default_start_date,
            Event_End_Date=settings.end_date or default_end_date,
            Covered_Type=settings.covered_type,
            Taxable_Type=settings.taxable_type,
            Procedure_Cost=settings.procedure_cost or procedure_info["procedure_cost"],
            Margin=margin,
            Margin_Rate=margin_rate,
            VAT=settings.vat,
            Validity_Period=settings.validity_period,
            Procedure_Grade=procedure_info.get("procedure_grade")  # Procedure_Grade 추가
        )
        
        db.add(product)
        db.flush()  # ID 생성을 위해 flush
        print(f"DEBUG: ProductEvent 생성 완료 - ID: {product.ID}")
        
        # Info_Event 생성 (설정에서 info 관련 필드가 제공된 경우)
        if (settings.event_name or settings.event_description or settings.event_precautions):
            try:
                # 기존 event_info_id가 있으면 사용, 없으면 새로 생성
                if settings.event_info_id:
                    print(f"DEBUG: 기존 Info_Event 사용 시도 - ID: {settings.event_info_id}")
                    # 기존 info가 실제로 존재하는지 확인
                    existing_info = db.query(InfoEvent).filter(InfoEvent.ID == settings.event_info_id).first()
                    if existing_info:
                        print(f"DEBUG: 기존 Info_Event 존재 확인 - ID: {settings.event_info_id}")
                        # ProductEvent의 Event_Info_ID 설정
                        product.Event_Info_ID = settings.event_info_id
                        print(f"DEBUG: ProductEvent.Event_Info_ID 설정됨: {product.Event_Info_ID}")
                    else:
                        print(f"DEBUG: 기존 Info_Event가 존재하지 않음 - ID: {settings.event_info_id}, 새로운 info 생성")
                        info_event = create_info_event(product.ID, settings, db)
                        # ProductEvent의 Event_Info_ID 업데이트
                        product.Event_Info_ID = info_event.ID
                        print(f"DEBUG: 새로운 Info_Event 생성 완료 - ID: {info_event.ID}")
                else:
                    info_event = create_info_event(product.ID, settings, db)
                    # ProductEvent의 Event_Info_ID 업데이트
                    product.Event_Info_ID = info_event.ID
                    print(f"DEBUG: 새로운 Info_Event 생성 완료 - ID: {info_event.ID}")
            except Exception as e:
                print(f"DEBUG: Info_Event 생성 실패: {str(e)}")
                raise e
        else:
            # info 관련 필드가 없어도 event_info_id가 있으면 설정
            if settings.event_info_id:
                print(f"DEBUG: Info 관련 필드 없음, 기존 event_info_id 사용 시도: {settings.event_info_id}")
                # 기존 info가 실제로 존재하는지 확인
                existing_info = db.query(InfoEvent).filter(InfoEvent.ID == settings.event_info_id).first()
                if existing_info:
                    print(f"DEBUG: 기존 Info_Event 존재 확인 - ID: {settings.event_info_id}")
                    product.Event_Info_ID = settings.event_info_id
                    print(f"DEBUG: ProductEvent.Event_Info_ID 설정됨: {product.Event_Info_ID}")
                else:
                    print(f"DEBUG: 기존 Info_Event가 존재하지 않음 - ID: {settings.event_info_id}")
                    # 기본 info 생성
                    info_event = create_info_event(product.ID, settings, db)
                    product.Event_Info_ID = info_event.ID
                    print(f"DEBUG: 기본 Info_Event 생성 완료 - ID: {info_event.ID}")
            else:
                print(f"DEBUG: Info 관련 필드도 없고, event_info_id도 없음")
        
        return product
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event Product 생성 중 오류가 발생했습니다: {str(e)}")

def get_next_product_id(product_type: str, db: Session) -> int:
    """
    다음 Product ID 생성
    
    Args:
        product_type: "standard" 또는 "event"
        db: 데이터베이스 세션
    
    Returns:
        int: 다음 사용 가능한 ID
    """
    try:
        if product_type == "standard":
            max_id = db.query(ProductStandard.ID).order_by(ProductStandard.ID.desc()).first()
        elif product_type == "event":
            max_id = db.query(ProductEvent.ID).order_by(ProductEvent.ID.desc()).first()
        else:
            raise ValueError(f"지원하지 않는 Product 타입입니다: {product_type}")
        
        return (max_id[0] + 1) if max_id and max_id[0] else 1
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Product ID 생성 중 오류가 발생했습니다: {str(e)}")

def update_standard_product_full(product_id: int, update_data: ProductUpdateRequest, db: Session) -> ProductStandard:
    """
    Standard Product 전체 수정 (모든 컬럼 수정 가능)
    
    Args:
        product_id: 수정할 Product ID
        update_data: 수정할 데이터
        db: 데이터베이스 세션
    
    Returns:
        ProductStandard: 수정된 Standard Product
    """
    try:
        product = db.query(ProductStandard).filter(ProductStandard.ID == product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Standard Product ID {product_id}를 찾을 수 없습니다.")
        
        # Product ID 변경 처리
        if update_data.new_id is not None and update_data.new_id != product_id:
            # 새로운 ID 중복 확인
            existing_product = db.query(ProductStandard).filter(ProductStandard.ID == update_data.new_id).first()
            if existing_product:
                raise HTTPException(status_code=400, detail=f"새로운 Product ID {update_data.new_id}가 이미 사용 중입니다.")
            
            # ID 변경
            product.ID = update_data.new_id
        
        # 기본 정보 수정
        if update_data.release is not None:
            product.Release = update_data.release
        
        if update_data.package_type is not None:
            product.Package_Type = update_data.package_type
        
        # 시술 참조 ID 수정
        if update_data.element_id is not None:
            product.Element_ID = update_data.element_id
            product.Bundle_ID = None
            product.Custom_ID = None
            product.Sequence_ID = None
        elif update_data.bundle_id is not None:
            product.Element_ID = None
            product.Bundle_ID = update_data.bundle_id
            product.Custom_ID = None
            product.Sequence_ID = None
        elif update_data.custom_id is not None:
            product.Element_ID = None
            product.Bundle_ID = None
            product.Custom_ID = update_data.custom_id
            product.Sequence_ID = None
        elif update_data.sequence_id is not None:
            product.Element_ID = None
            product.Bundle_ID = None
            product.Custom_ID = None
            product.Sequence_ID = update_data.sequence_id
        
        # Info 참조 ID 수정
        if update_data.standard_info_id is not None:
            product.Standard_Info_ID = update_data.standard_info_id
        
        # 가격 정보 수정
        if update_data.sell_price is not None:
            product.Sell_Price = update_data.sell_price
        
        if update_data.original_price is not None:
            product.Original_Price = update_data.original_price
        
        if update_data.discount_rate is not None:
            product.Discount_Rate = update_data.discount_rate
        
        if update_data.procedure_cost is not None:
            product.Procedure_Cost = update_data.procedure_cost
        
        if update_data.margin is not None:
            product.Margin = update_data.margin
        
        if update_data.margin_rate is not None:
            product.Margin_Rate = update_data.margin_rate
        
        # 날짜 정보 수정
        if update_data.start_date is not None:
            product.Standard_Start_Date = update_data.start_date
        
        if update_data.end_date is not None:
            product.Standard_End_Date = update_data.end_date
        
        # 기타 정보 수정
        if update_data.validity_period is not None:
            product.Validity_Period = update_data.validity_period
        
        if update_data.vat is not None:
            product.VAT = update_data.vat
        
        if update_data.covered_type is not None:
            product.Covered_Type = update_data.covered_type
        
        if update_data.taxable_type is not None:
            product.Taxable_Type = update_data.taxable_type
        
        # Info_Standard 정보 수정
        print(f"=== Info_Standard 수정 조건 확인 ===")
        print(f"info_standard_id: {update_data.info_standard_id}")
        print(f"product_standard_name: {update_data.product_standard_name}")
        print(f"product_standard_description: {update_data.product_standard_description}")
        print(f"precautions: {update_data.precautions}")
        
        if (update_data.info_standard_id is not None or 
            update_data.product_standard_name is not None or 
            update_data.product_standard_description is not None or 
            update_data.precautions is not None):
            
            print(f"=== Info_Standard 수정 시작 ===")
            # 현재 연결된 Info_Standard 조회
            current_info_id = product.Standard_Info_ID
            print(f"현재 연결된 Standard_Info_ID: {current_info_id}")
            
            if current_info_id:
                print(f"기존 Info_Standard 조회 시도: ID {current_info_id}")
                info_standard = db.query(InfoStandard).filter(InfoStandard.ID == current_info_id).first()
                print(f"조회된 Info_Standard: {info_standard}")
                
                if info_standard:
                    print(f"기존 Info_Standard 정보 업데이트 시작")
                    # Info_Standard 정보 업데이트
                    if update_data.product_standard_name is not None:
                        print(f"Product_Standard_Name 업데이트: {info_standard.Product_Standard_Name} -> {update_data.product_standard_name}")
                        info_standard.Product_Standard_Name = update_data.product_standard_name
                    if update_data.product_standard_description is not None:
                        print(f"Product_Standard_Description 업데이트: {info_standard.Product_Standard_Description} -> {update_data.product_standard_description}")
                        info_standard.Product_Standard_Description = update_data.product_standard_description
                    if update_data.precautions is not None:
                        print(f"Precautions 업데이트: {info_standard.Precautions} -> {update_data.precautions}")
                        info_standard.Precautions = update_data.precautions
                    print(f"기존 Info_Standard 정보 업데이트 완료")
                else:
                    print(f"기존 Info_Standard가 존재하지 않음, 새로 생성")
                    # Info_Standard가 존재하지 않는 경우 새로 생성
                    new_info = InfoStandard(
                        Release=1,
                        Product_Standard_ID=product.ID,
                        Product_Standard_Name=update_data.product_standard_name or f"Product {product.ID}",
                        Product_Standard_Description=update_data.product_standard_description or "",
                        Precautions=update_data.precautions or ""
                    )
                    db.add(new_info)
                    db.flush()  # ID 생성을 위해 flush
                    product.Standard_Info_ID = new_info.ID
                    print(f"새 Info_Standard 생성 완료, ID: {new_info.ID}")
            else:
                print(f"Info_Standard가 연결되지 않음, 새로 생성")
                # Info_Standard가 연결되지 않은 경우 새로 생성
                new_info = InfoStandard(
                    Release=1,
                    Product_Standard_ID=product.ID,
                    Product_Standard_Name=update_data.product_standard_name or f"Product {product.ID}",
                    Product_Standard_Description=update_data.product_standard_description or "",
                    Precautions=update_data.precautions or ""
                )
                db.add(new_info)
                db.flush()  # ID 생성을 위해 flush
                product.Standard_Info_ID = new_info.ID
                print(f"새 Info_Standard 생성 완료, ID: {new_info.ID}")
            
            print(f"=== Info_Standard 수정 완료 ===")
        else:
            print(f"=== Info_Standard 수정 조건 불충족, 수정하지 않음 ===")
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standard Product 수정 중 오류가 발생했습니다: {str(e)}")

async def get_standard_product_detail(product_id: int, db: Session):
    """Standard Product 상세 정보 조회 (내부 함수)"""
    try:
        product = db.query(ProductStandard).filter(ProductStandard.ID == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Standard Product ID {product_id}를 찾을 수 없습니다.")
        
        # Info 정보 조회
        info_standard = get_product_info(product, db)
        
        # Procedure 정보 조회
        procedure_info = get_procedure_info(product, db)
        
        # 연결된 시술 상세 정보 조회 (Enhanced)
        procedure_detail = get_procedure_detail_enhanced(product, db)
        
        return {
            "status": "success",
            "message": "Standard Product 상세 조회 완료",
            "data": {
                "id": product.ID,
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": product.Standard_Start_Date,
                "end_date": product.Standard_End_Date,
                "validity_period": product.Validity_Period,
                "vat": product.VAT,
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
                "standard_info_id": product.Standard_Info_ID,
                "info_standard": info_standard,
                "procedure_info": procedure_info,
                "procedure_detail": procedure_detail
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standard Product 조회 중 오류가 발생했습니다: {str(e)}")

async def get_event_product_detail(product_id: int, db: Session):
    """Event Product 상세 정보 조회 (내부 함수)"""
    try:
        product = db.query(ProductEvent).filter(ProductEvent.ID == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail=f"Event Product ID {product_id}를 찾을 수 없습니다.")
        
        # 디버깅을 위한 로그
        print(f"DEBUG: Event Product ID: {product.ID}")
        print(f"DEBUG: Event Product Element_ID: {getattr(product, 'Element_ID', None)}")
        print(f"DEBUG: Event Product Bundle_ID: {getattr(product, 'Bundle_ID', None)}")
        print(f"DEBUG: Event Product Custom_ID: {getattr(product, 'Custom_ID', None)}")
        print(f"DEBUG: Event Product Sequence_ID: {getattr(product, 'Sequence_ID', None)}")
        
        # Info 정보 조회
        info_event = get_product_info(product, db)
        
        # Procedure 정보 조회
        procedure_info = get_procedure_info(product, db)
        
        # 연결된 시술 상세 정보 조회 (Enhanced)
        procedure_detail = get_procedure_detail_enhanced(product, db)
        
        return {
            "status": "success",
            "message": "Event Product 상세 조회 완료",
            "data": {
                "id": product.ID,
                "sell_price": product.Sell_Price,
                "original_price": product.Original_Price,
                "discount_rate": product.Discount_Rate,
                "start_date": product.Event_Start_Date,
                "end_date": product.Event_End_Date,
                "validity_period": product.Validity_Period,
                "vat": product.VAT,
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
                "event_info_id": product.Event_Info_ID,
                "info_event": info_event,
                "procedure_info": procedure_info,
                "procedure_detail": procedure_detail
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event Product 조회 중 오류가 발생했습니다: {str(e)}")

def update_event_product_full(product_id: int, update_data: ProductUpdateRequest, db: Session) -> ProductEvent:
    """
    Event Product 전체 수정 (모든 컬럼 수정 가능)
    
    Args:
        product_id: 수정할 Product ID
        update_data: update_data: 수정할 데이터
        db: 데이터베이스 세션
    
    Returns:
        ProductEvent: 수정된 Event Product
    """
    try:
        print(f"=== update_event_product_full 시작 ===")
        print(f"Product ID: {product_id}")
        
        product = db.query(ProductEvent).filter(ProductEvent.ID == product_id).first()
        if not product:
            print(f"=== Product를 찾을 수 없음: {product_id} ===")
            raise HTTPException(status_code=404, detail=f"Event Product ID {product_id}를 찾을 수 없습니다.")
        
        print(f"=== 기존 Product 찾음: {product.ID} ===")
        
        # Product ID 변경 처리
        if update_data.new_id is not None and update_data.new_id != product_id:
            print(f"=== Product ID 변경 시도: {product_id} -> {update_data.new_id} ===")
            # 새로운 ID 중복 확인
            existing_product = db.query(ProductEvent).filter(ProductEvent.ID == update_data.new_id).first()
            if existing_product:
                print(f"=== 새로운 ID가 이미 사용 중: {update_data.new_id} ===")
                raise HTTPException(status_code=400, detail=f"새로운 Product ID {update_data.new_id}가 이미 사용 중입니다.")
            
            # ID 변경
            product.ID = update_data.new_id
            print(f"=== Product ID 변경 완료: {update_data.new_id} ===")
        
        # 기본 정보 수정
        if update_data.release is not None:
            product.Release = update_data.release
        
        if update_data.package_type is not None:
            product.Package_Type = update_data.package_type
        
        # 시술 참조 ID 수정
        if update_data.element_id is not None:
            product.Element_ID = update_data.element_id
            product.Bundle_ID = None
            product.Custom_ID = None
            product.Sequence_ID = None
        elif update_data.bundle_id is not None:
            product.Element_ID = None
            product.Bundle_ID = update_data.bundle_id
            product.Custom_ID = None
            product.Sequence_ID = None
        elif update_data.custom_id is not None:
            product.Element_ID = None
            product.Bundle_ID = None
            product.Custom_ID = update_data.custom_id
            product.Sequence_ID = None
        elif update_data.sequence_id is not None:
            product.Element_ID = None
            product.Bundle_ID = None
            product.Custom_ID = None
            product.Sequence_ID = update_data.sequence_id
        
        # Info 참조 ID 수정
        if update_data.event_info_id is not None:
            product.Event_Info_ID = update_data.event_info_id
        
        # 가격 정보 수정
        if update_data.sell_price is not None:
            product.Sell_Price = update_data.sell_price
        
        if update_data.original_price is not None:
            product.Original_Price = update_data.original_price
        
        if update_data.discount_rate is not None:
            product.Discount_Rate = update_data.discount_rate
        
        if update_data.procedure_cost is not None:
            product.Procedure_Cost = update_data.procedure_cost
        
        if update_data.margin is not None:
            product.Margin = update_data.margin
        
        if update_data.margin_rate is not None:
            product.Margin_Rate = update_data.margin_rate
        
        # 날짜 정보 수정
        if update_data.start_date is not None:
            product.Event_Start_Date = update_data.start_date
        
        if update_data.end_date is not None:
            product.Event_End_Date = update_data.end_date
        
        # 기타 정보 수정
        if update_data.validity_period is not None:
            product.Validity_Period = update_data.validity_period
        
        if update_data.vat is not None:
            product.VAT = update_data.vat
        
        if update_data.covered_type is not None:
            product.Covered_Type = update_data.covered_type
        
        if update_data.taxable_type is not None:
            product.Taxable_Type = update_data.taxable_type
        
        # Info_Event 정보 수정
        print(f"=== Info_Event 수정 조건 확인 ===")
        print(f"event_info_id: {update_data.event_info_id}")
        print(f"event_name: {update_data.event_name}")
        print(f"event_description: {update_data.event_description}")
        print(f"event_precautions: {update_data.event_precautions}")
        
        if (update_data.event_info_id is not None or 
            update_data.event_name is not None or 
            update_data.event_description is not None or 
            update_data.event_precautions is not None):
            
            print(f"=== Info_Event 수정 시작 ===")
            # 현재 연결된 Info_Event 조회
            current_info_id = product.Event_Info_ID
            print(f"현재 연결된 Event_Info_ID: {current_info_id}")
            
            if current_info_id:
                print(f"기존 Info_Event 조회 시도: ID {current_info_id}")
                info_event = db.query(InfoEvent).filter(InfoEvent.ID == current_info_id).first()
                print(f"조회된 Info_Event: {info_event}")
                
                if info_event:
                    print(f"기존 Info_Event 정보 업데이트 시작")
                    # Info_Event 정보 업데이트
                    if update_data.event_name is not None:
                        print(f"Event_Name 업데이트: {info_event.Event_Name} -> {update_data.event_name}")
                        info_event.Event_Name = update_data.event_name
                    if update_data.event_description is not None:
                        print(f"Event_Description 업데이트: {info_event.Event_Description} -> {update_data.event_description}")
                        info_event.Event_Description = update_data.event_description
                    if update_data.event_precautions is not None:
                        print(f"Precautions 업데이트: {info_event.Precautions} -> {update_data.event_precautions}")
                        info_event.Precautions = update_data.event_precautions
                    print(f"기존 Info_Event 정보 업데이트 완료")
                else:
                    print(f"기존 Info_Event가 존재하지 않음, 새로 생성")
                    # Info_Event가 존재하지 않는 경우 새로 생성
                    new_info = InfoEvent(
                        Release=1,
                        Event_ID=product.ID,
                        Event_Name=update_data.event_name or f"Event {product.ID}",
                        Event_Description=update_data.event_description or "",
                        Precautions=update_data.event_precautions or ""
                    )
                    db.add(new_info)
                    db.flush()  # ID 생성을 위해 flush
                    product.Event_Info_ID = new_info.ID
                    print(f"새 Info_Event 생성 완료, ID: {new_info.ID}")
            else:
                print(f"Info_Event가 연결되지 않음, 새로 생성")
                # Info_Event가 연결되지 않은 경우 새로 생성
                new_info = InfoEvent(
                    Release=1,
                    Event_ID=product.ID,
                    Event_Name=update_data.event_name or f"Event {product.ID}",
                    Event_Description=update_data.event_description or "",
                    Precautions=update_data.event_precautions or ""
                )
                db.add(new_info)
                db.flush()  # ID 생성을 위해 flush
                product.Event_Info_ID = new_info.ID
                print(f"새 Info_Event 생성 완료, ID: {new_info.ID}")
            
            print(f"=== Info_Event 수정 완료 ===")
        else:
            print(f"=== Info_Event 수정 조건 불충족, 수정하지 않음 ===")
        
        return product
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event Product 수정 중 오류가 발생했습니다: {str(e)}")



@products_router.get("/info/standard")
async def get_standard_info_list(
    search: Optional[str] = Query(None, description="검색어"),
    db: Session = Depends(get_db)
):
    """Standard Info 목록 조회"""
    try:
        query = db.query(InfoStandard).filter(InfoStandard.Release == 1)
        
        if search:
            query = query.filter(
                or_(
                    InfoStandard.Product_Standard_Name.contains(search),
                    InfoStandard.Product_Standard_Description.contains(search)
                )
            )
        
        info_list = query.all()
        
        data = [
            {
                "id": info.ID,
                "name": info.Product_Standard_Name,
                "description": info.Product_Standard_Description,
                "precautions": info.Precautions
            } for info in info_list
        ]
        
        return {
            "status": "success",
            "message": "Standard Info 목록 조회 완료",
            "data": data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standard Info 조회 중 오류가 발생했습니다: {str(e)}")

@products_router.get("/info/event")
async def get_event_info_list(
    search: Optional[str] = Query(None, description="검색어"),
    db: Session = Depends(get_db)
):
    """Event Info 목록 조회"""
    try:
        query = db.query(InfoEvent).filter(InfoEvent.Release == 1)
        
        if search:
            query = query.filter(
                or_(
                    InfoEvent.Event_Name.contains(search),
                    InfoEvent.Event_Description.contains(search)
                )
            )
        
        info_list = query.all()
        
        data = [
            {
                "id": info.ID,
                "name": info.Event_Name,
                "description": info.Event_Description,
                "precautions": info.Precautions
            } for info in info_list
        ]
        
        return {
            "status": "success",
            "message": "Event Info 목록 조회 완료",
            "data": data
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event Info 조회 중 오류가 발생했습니다: {str(e)}")

@products_router.get("/info/standard/{info_id}")
async def get_standard_info_detail(info_id: int, db: Session = Depends(get_db)):
    """Standard Info 상세 조회"""
    try:
        info = db.query(InfoStandard).filter(
            InfoStandard.ID == info_id,
            InfoStandard.Release == 1
        ).first()
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Standard Info ID {info_id}를 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "message": "Standard Info 상세 조회 완료",
            "data": {
                "id": info.ID,
                "name": info.Product_Standard_Name,
                "description": info.Product_Standard_Description,
                "precautions": info.Precautions
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Standard Info 상세 조회 중 오류가 발생했습니다: {str(e)}")

@products_router.get("/info/event/{info_id}")
async def get_event_info_detail(info_id: int, db: Session = Depends(get_db)):
    """Event Info 상세 조회"""
    try:
        info = db.query(InfoEvent).filter(
            InfoEvent.ID == info_id,
            InfoEvent.Release == 1
        ).first()
        
        if not info:
            raise HTTPException(status_code=404, detail=f"Event Info ID {info_id}를 찾을 수 없습니다.")
        
        return {
            "status": "success",
            "message": "Event Info 상세 조회 완료",
            "data": {
                "id": info.ID,
                "name": info.Event_Name,
                "description": info.Event_Description,
                "precautions": info.Precautions
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Event Info 상세 조회 중 오류가 발생했습니다: {str(e)}")

def create_info_standard(
    product_id: int,
    settings: StandardSettingsRequest,
    db: Session
) -> InfoStandard:
    """
    Info_Standard 생성
    
    Args:
        product_id: Product ID
        settings: Standard 설정
        db: 데이터베이스 세션
    
    Returns:
        InfoStandard: 생성된 Info_Standard
    """
    try:
        # Info_Standard 생성 시 ID를 standard_info_id와 동일하게 설정
        info_standard = InfoStandard(
            ID=settings.standard_info_id,  # standard_info_id와 동일한 ID 사용
            Release=1,
            Product_Standard_ID=product_id,
            Product_Standard_Name=settings.product_standard_name or f"표준 상품 {product_id}",
            Product_Standard_Description=settings.product_standard_description or "",
            Precautions=settings.precautions or ""
        )
        
        db.add(info_standard)
        db.flush()  # ID 생성을 위해 flush
        
        return info_standard
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Info_Standard 생성 중 오류가 발생했습니다: {str(e)}")

def create_info_event(
    product_id: int,
    settings: EventSettingsRequest,
    db: Session
) -> InfoEvent:
    """
    Info_Event 생성
    
    Args:
        product_id: Product ID
        settings: Event 설정
        db: 데이터베이스 세션
    
    Returns:
        InfoEvent: 생성된 Info_Event
    """
    try:
        # Info_Event 생성 시 ID를 event_info_id와 동일하게 설정
        info_event = InfoEvent(
            ID=settings.event_info_id,  # event_info_id와 동일한 ID 사용
            Release=1,
            Event_ID=product_id,
            Event_Name=settings.event_name or f"이벤트 상품 {product_id}",
            Event_Description=settings.event_description or "",
            Precautions=settings.event_precautions or ""
        )
        
        db.add(info_event)
        db.flush()  # ID 생성을 위해 flush
        
        return info_event
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Info_Event 생성 중 오류가 발생했습니다: {str(e)}")