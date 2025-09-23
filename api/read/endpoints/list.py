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
from ..services.list_service import build_standard_product_data, build_event_product_data, get_procedures_batch_optimized

router = APIRouter()


"""
    상품 전체 목록 조회:
        
        Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
        프론트엔드에서 상품 목록을 띄우기 위한 API입니다.
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
            
            # standard_products의 ID를 리스트로 변환
            standard_ids = [p.ID for p in standard_products]
            
            # standard_ids를 파라미터로 하여 시술 정보 일괄 조회
            standard_procedure_data = get_procedures_batch_optimized(db, standard_ids, "standard")

            # get_procedures_batch_optimized 함수를 통해 시술 정보 일괄 조회 완료
            # return 값: {key: {'procedure_names': ['시술1', '시술2'], 'class_types': []}}
            
            # 모든 standard_product를 순회하면서 build_standard_product_data 함수를 통해 상품 데이터 구성
            for standard_product in standard_products:
                standard_product_data = build_standard_product_data(
                    standard_product, 
                    db, 
                    standard_procedure_data.get(standard_product.ID, {})   # ex) {"procedure_names": ["포텐자 모공", "디오레 피부재생"], "class_types": ["제모", "피부재생"]}
                )
                
                # standard_product_data: {
                #     "ID": 1,
                #     "Product_Type": "standard",
                #     "Package_Type": "패키지",
                #     "Sell_Price": 100000,
                #     "Original_Price": 100000,
                # }

                # products 리스트에 standard_product_data를 추가
                products.append(standard_product_data)
        

        if product_type in ["all", "event"]:
            # ProductEvent 테이블에서 모든 데이터를 조회, Event_Start_Date 기준 내림차순 정렬
            event_products = db.query(ProductEvent).order_by(
                desc(ProductEvent.Event_Start_Date)
            ).all()
            
            # event_products의 ID를 리스트로 변환
            event_ids = [p.ID for p in event_products]

            # event_ids를 파라미터로 하여 시술 정보 일괄 조회
            event_procedure_data = get_procedures_batch_optimized(db, event_ids, "event")

            # get_procedures_batch_optimized 함수를 통해 시술 정보 일괄 조회 완료
            # return 값: {key: {'procedure_names': ['시술1', '시술2'], 'class_types': []}}
            
            # 모든 event_product를 순회하면서 build_event_product_data 함수를 통해 상품 데이터 구성
            
            for event_product in event_products:
                event_product_data = build_event_product_data(
                    event_product, 
                    db, 
                    event_procedure_data.get(event_product.ID, {})   # ex) {"procedure_names": ["포텐자 모공", "디오레 피부재생"], "class_types": ["제모", "피부재생"]}
                )

                # products 리스트에 event_product_data를 추가
                products.append(event_product_data)
        

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

