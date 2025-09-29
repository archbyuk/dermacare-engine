"""
    [ '상품 전체 목록 조회' 엔드포인트 ]
    Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
"""

import pprint
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from db.session import get_db
from db.models.product import ProductEvent, ProductStandard
from ..schema import ProductListResponse, PaginationInfo
from ..services.list_service import build_standard_products_optimized, build_event_products_optimized

router = APIRouter()


"""
    상품 전체 목록 조회:
        
        Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
        프론트엔드에서 상품 목록을 띄우기 위한 API입니다.

    성능개선(2025.09.24): 로딩 시간 4~5초 > 평균 1.5s로 감소
        1. N+1 쿼리 문제 해결
        2. 최적화된 데이터 구조 사용
"""

@router.get("/products", response_model=ProductListResponse)
def get_products(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(30, ge=1, le=200000, description="페이지 크기"),
    product_type: str = Query("all", description="상품 타입 (all | standard | event)"),
    db: Session = Depends(get_db)
):
    
    try:
        # 상품 타입 검증: 무조건 all, standard, event 중 하나여야 함.
        if product_type not in ["all", "standard", "event"]:
            raise HTTPException(status_code=400, detail="잘못된 상품 타입입니다. (all/standard/event 중 선택)")
        
        # 상품 목록을 저장하는 리스트
        products = []
        
        # 1. 상품 데이터만 먼저 조회 (한 번에 모든 데이터 가져오기)
        if product_type in ["all", "standard"]:
            # ProductStandard 테이블에서 모든 데이터를 조회, Standard_Start_Date 기준 내림차순 정렬
            standard_products = db.query(ProductStandard).order_by(
                desc(ProductStandard.Standard_Start_Date)
            ).all()
            
            # 통합된 최적화 함수 사용
            standard_product_data = build_standard_products_optimized(standard_products, db)
            products.extend(standard_product_data)
        

        if product_type in ["all", "event"]:
            # ProductEvent 테이블에서 모든 데이터를 조회, Event_Start_Date 기준 내림차순 정렬
            event_products = db.query(ProductEvent).order_by(
                desc(ProductEvent.Event_Start_Date)
            ).all()
            
            # 통합된 최적화 함수 사용
            event_product_data = build_event_products_optimized(event_products, db)
            products.extend(event_product_data)
        

        # 총 개수 조회
        total_count = 0
        
        # 진짜 테이블의 총 개수 조회
        # if product_type in ["all", "standard"]:
        #     total_count += db.query(ProductStandard).count()
       
        # if product_type in ["all", "event"]:
        #     total_count += db.query(ProductEvent).count()

        total_count = len(products)
        
        # 상품 전체 데이터 목록 리스트
        list_products = products
        
        # 상품 목록 조회 완료 - ProductListResponse 모델 사용
        return ProductListResponse(
            status="success",
            message="상품 전체 목록 조회 완료",
            data=list_products,
            # 페이지네이션 정보, 곧 추릴듯 (2025.09.23)
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

