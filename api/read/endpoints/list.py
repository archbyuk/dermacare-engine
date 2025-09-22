"""
    [ '상품 목록 조회' 엔드포인트 ]
    Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from db.session import get_db
from db.models.product import ProductEvent, ProductStandard
from ..schema import ProductListResponse, PaginationInfo
from ..services.list_service import build_standard_product_data, build_event_product_data

router = APIRouter()


"""
    상품 목록 조회:
        
        Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
        프론트엔드에서 상품 목록을 띄우기 위한 API입니다.
"""
@router.get("/products", response_model=ProductListResponse)
def get_products(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(30, ge=1, le=200000, description="페이지 크기"),
    product_type: str = Query("all", description="상품 타입 (all/standard/event)"),
    db: Session = Depends(get_db)
):
    
    try:
        # 상품 타입 검증
        if product_type not in ["all", "standard", "event"]:
            raise HTTPException(status_code=400, detail="잘못된 상품 타입입니다. (all/standard/event 중 선택)")
        
        # 상품 목록을 저장하는 리스트
        products = []
        
        # Product_Standard 조회
        if product_type in ["all", "standard"]:
            standard_products = db.query(ProductStandard).order_by(
                desc(ProductStandard.Standard_Start_Date)  # Standard_Start_Date 기준 최신순
            ).all()

            # standard_products가 있을 경우, 내부의 모든 standard_product를 순회하면서 build_standard_product_data 함수를 호출하여 standard_product_data를 생성
            for standard_product in standard_products:
                standard_product_data = build_standard_product_data(standard_product, db)
                products.append(standard_product_data)
        
        
        # Product_Event 조회
        if product_type in ["all", "event"]:
            event_products = db.query(ProductEvent).order_by(
                desc(ProductEvent.Event_Start_Date)     # Event_Start_Date 기준 최신순
            ).all()
            
            # event_products가 있을 경우, 내부의 모든 event_product를 순회하면서 build_event_product_data 함수를 호출하여 event_product_data를 생성
            for event_product in event_products:
                event_product_data = build_event_product_data(event_product, db)
                products.append(event_product_data)
        
        
        # 페이지네이션
        total_count = len(products)
        offset = (page - 1) * page_size 
        paginated_products = products[offset:offset + page_size]
        
        # 상품 목록 조회 완료 - ProductListResponse 모델 사용
        return ProductListResponse(
            status="success",
            message="상품 목록 조회 완료",
            data=paginated_products,
            pagination=PaginationInfo(
                page=page,
                page_size=page_size,
                total_count=total_count,
                total_pages=(total_count + page_size - 1) // page_size
            )
        )
        
    except HTTPException:
        raise
   
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상품 목록 조회 중 오류 발생: {str(e)}"
        )