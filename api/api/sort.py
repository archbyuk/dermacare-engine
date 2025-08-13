from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional

from db.session import get_db
from db.models.product import ProductStandard, ProductEvent
from db.models.info import InfoStandard, InfoEvent

sort_router = APIRouter(prefix="/sort", tags=["정렬"])

"""
    상품 정렬 API
    
    다양한 기준으로 상품을 정렬하여 반환합니다.
    프론트엔드의 드롭다운 정렬 기능을 위한 API입니다.
"""

@sort_router.get("/products")
def sort_products(
    sort_by: str = Query(..., description="정렬 기준 (price, name, date, type, discount)"),
    order: str = Query("asc", description="정렬 순서 (asc, desc)"),
    product_type: str = Query("all", description="상품 타입 (all/standard/event)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(30, ge=1, le=1000, description="페이지 크기"),
    db: Session = Depends(get_db)
):
    try:
        # 파라미터 검증: 정렬 기준 확인
        if sort_by not in ["price", "name", "date", "type", "discount"]:
            raise HTTPException(
                status_code=400, 
                detail="잘못된 정렬 기준입니다. (price, name, date, type, discount 중 선택)"
            )
        
        # 파라미터 검증: 정렬 순서 확인
        if order not in ["asc", "desc"]:
            raise HTTPException(
                status_code=400, 
                detail="잘못된 정렬 순서입니다. (asc, desc 중 선택)"
            )
        
        # 파라미터 검증: 상품 타입 확인
        if product_type not in ["all", "standard", "event"]:
            raise HTTPException(
                status_code=400, 
                detail="잘못된 상품 타입입니다. (all/standard/event 중 선택)"
            )
        
        # 정렬 순서 설정
        sort_order = desc if order == "desc" else asc
        
        # 상품 타입별 리스트 분리
        standard_products = []
        event_products = []
        
        # Standard 상품 조회 및 정렬
        if product_type in ["all", "standard"]:
            standard_query = db.query(ProductStandard)
            
            # ==== 정렬 기준별 쿼리 설정 ==== #

            # 가격 정렬
            if sort_by == "price":
                standard_query = standard_query.order_by(sort_order(ProductStandard.Sell_Price))
            
            # 이름 정렬
            elif sort_by == "name":
                # Info 테이블과 조인하여 이름으로 정렬
                standard_query = standard_query.join(InfoStandard, ProductStandard.Standard_Info_ID == InfoStandard.ID)
                standard_query = standard_query.order_by(sort_order(InfoStandard.Product_Standard_Name))
            
            # 날짜 정렬
            elif sort_by == "date":
                standard_query = standard_query.order_by(sort_order(ProductStandard.Standard_Start_Date))
            
            # 타입 정렬
            elif sort_by == "type":
                standard_query = standard_query.order_by(sort_order(ProductStandard.Package_Type))
            
            # 할인율 정렬
            elif sort_by == "discount":
                standard_query = standard_query.order_by(sort_order(ProductStandard.Discount_Rate))
            
            # 정렬된 Standard 상품 데이터 구성
            standard_products_raw = standard_query.all()
            
            # 정렬된 Standard 상품 데이터 구성
            for standard_product in standard_products_raw:
                product_data = {
                    "ID": standard_product.ID,
                    "Product_Type": "standard",
                    "Package_Type": standard_product.Package_Type,
                    "Procedure_Cost": standard_product.Procedure_Cost,
                    "Sell_Price": standard_product.Sell_Price,
                    "Original_Price": standard_product.Original_Price,
                    "Standard_Start_Date": standard_product.Standard_Start_Date,
                    "Standard_End_Date": standard_product.Standard_End_Date,
                    "Validity_Period": standard_product.Validity_Period,
                    "Product_Name": None
                }
                
                # 할인율 정렬 시에만 Discount_Rate 포함
                if sort_by == "discount":
                    product_data["Discount_Rate"] = standard_product.Discount_Rate
                
                # Info 테이블에서 상품명 가져오기
                if standard_product.Standard_Info_ID:
                    standard_info = db.query(InfoStandard).filter(
                        InfoStandard.ID == standard_product.Standard_Info_ID
                    ).first()
                    
                    if standard_info:
                        product_data["Product_Name"] = standard_info.Product_Standard_Name
                
                # 정렬된 Standard 상품 데이터 구성
                standard_products.append(product_data)
        
        
        # Event 상품 조회 및 정렬
        if product_type in ["all", "event"]:
            event_query = db.query(ProductEvent)
            
            # ==== 정렬 기준별 쿼리 설정 ==== # 

            # 가격 정렬
            if sort_by == "price":
                event_query = event_query.order_by(sort_order(ProductEvent.Sell_Price))
            
            # 이름 정렬
            elif sort_by == "name":
                # Info 테이블과 조인하여 이름으로 정렬
                event_query = event_query.join(InfoEvent, ProductEvent.Event_Info_ID == InfoEvent.ID)
                event_query = event_query.order_by(sort_order(InfoEvent.Event_Name))
            
            # 날짜 정렬
            elif sort_by == "date":
                event_query = event_query.order_by(sort_order(ProductEvent.Event_Start_Date))
            
            # 타입 정렬
            elif sort_by == "type":
                event_query = event_query.order_by(sort_order(ProductEvent.Package_Type))
            
            # 할인율 정렬
            elif sort_by == "discount":
                event_query = event_query.order_by(sort_order(ProductEvent.Discount_Rate))
            
            # 정렬된 Event 상품 데이터 구성
            event_products_raw = event_query.all()
            
            # 정렬된 Event 상품 데이터 구성
            for event_product in event_products_raw:
                event_data = {
                    "ID": event_product.ID,
                    "Product_Type": "event",
                    "Package_Type": event_product.Package_Type,
                    "Procedure_Cost": event_product.Procedure_Cost,
                    "Sell_Price": event_product.Sell_Price,
                    "Original_Price": event_product.Original_Price,
                    "Event_Start_Date": event_product.Event_Start_Date,
                    "Event_End_Date": event_product.Event_End_Date,
                    "Validity_Period": event_product.Validity_Period,
                    "Product_Name": None
                }
                
                # 할인율 정렬 시에만 Discount_Rate 포함
                if sort_by == "discount":
                    event_data["Discount_Rate"] = event_product.Discount_Rate
                
                # Info 테이블에서 상품명 가져오기
                if event_product.Event_Info_ID:
                    event_info = db.query(InfoEvent).filter(
                        InfoEvent.ID == event_product.Event_Info_ID
                    ).first()
                    
                    if event_info:
                        event_data["Product_Name"] = event_info.Event_Name
                
                event_products.append(event_data)
        
        # 요청된 상품 타입에 따라 최종 결과 구성: Standard만
        if product_type == "standard":
            products = standard_products
        
        # 요청된 상품 타입에 따라 최종 결과 구성: Event만
        elif product_type == "event":
            products = event_products
        
        # product_type == "all": Standard + Event 모두
        else:
            products = standard_products + event_products
        
        # 페이지네이션 적용
        total_count = len(products)
        total_pages = (total_count + page_size - 1) // page_size
        
        start_index = (page - 1) * page_size
        end_index = start_index + page_size
        paginated_products = products[start_index:end_index]
        
        return {
            "status": "success",
            "message": f"상품 정렬 완료 ({sort_by} {order})",
            "data": paginated_products,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": total_pages
            },
            "sort_info": {
                "sort_by": sort_by,
                "order": order,
                "product_type": product_type
            }
        }
        
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"상품 정렬 중 오류 발생: {str(e)}")
