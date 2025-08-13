from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional

from db.session import get_db
from db.models.product import ProductStandard, ProductEvent
from db.models.info import InfoStandard, InfoEvent
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence

filter_router = APIRouter(prefix="/filter", tags=["필터"])

"""
    상품 필터 API
    
    Class_Major, Class_Sub, Class_Detail, Class_Type 기준으로 상품을 필터링함.
    프론트엔드의 카테고리별 필터 기능을 위한 API
"""

@filter_router.get("/products")
def filter_products(
    class_major: Optional[str] = Query(None, description="메이저 분류"),
    class_sub: Optional[str] = Query(None, description="서브 분류"),
    class_detail: Optional[str] = Query(None, description="상세 분류"),
    class_type: Optional[str] = Query(None, description="속성"),
    product_type: str = Query("all", description="상품 타입 (all/standard/event)"),
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(30, ge=1, le=1000, description="페이지 크기"),
    db: Session = Depends(get_db)
):
    try:
        # 파라미터 검증: 상품 타입 확인
        if product_type not in ["all", "standard", "event"]:
            raise HTTPException(
                status_code=400, 
                detail="잘못된 상품 타입입니다. (all/standard/event 중 선택)"
            )
        
        # 파라미터 검증: 페이지네이션 값 확인
        if page < 1:
            raise HTTPException(
                status_code=400,
                detail="페이지 번호는 1 이상이어야 합니다."
            )
        
        if page_size < 1 or page_size > 1000:
            raise HTTPException(
                status_code=400,
                detail="페이지 크기는 1 이상 1000 이하여야 합니다."
            )
        
        # 필터 조건이 하나도 없으면 에러
        if not any([class_major, class_sub, class_detail, class_type]):
            raise HTTPException(
                status_code=400,
                detail="최소 하나의 필터 조건이 필요합니다. (class_major, class_sub, class_detail, class_type 중 선택)"
            )
        
        # 상품 타입별 리스트 분리
        standard_products = []
        event_products = []
        
        # Standard 상품 필터링
        if product_type in ["all", "standard"]:
            try:
                # 기본 쿼리: ProductStandard와 ProcedureElement 조인
                standard_query = db.query(ProductStandard).distinct()
                
                # 단일시술인 경우 직접 조인
                standard_query = standard_query.join(
                    ProcedureElement, 
                    ProductStandard.Element_ID == ProcedureElement.ID
                )
                
                # class_major 필터 조건 적용
                if class_major:
                    standard_query = standard_query.filter(ProcedureElement.Class_Major == class_major)
                
                # class_sub 필터 조건 적용
                if class_sub:
                    standard_query = standard_query.filter(ProcedureElement.Class_Sub == class_sub)
                
                # class_detail 필터 조건 적용
                if class_detail:
                    standard_query = standard_query.filter(ProcedureElement.Class_Detail == class_detail)
                
                # class_type 필터 조건 적용
                if class_type:
                    standard_query = standard_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 번들/커스텀/시퀀스에 포함된 시술도 검색
                bundle_query = db.query(ProductStandard).distinct()
                custom_query = db.query(ProductStandard).distinct()
                sequence_query = db.query(ProductStandard).distinct()
                
                # 번들 내 시술 검색
                if any([class_major, class_sub, class_detail, class_type]):
                    bundle_query = bundle_query.join(
                        ProcedureBundle, 
                        ProductStandard.Bundle_ID == ProcedureBundle.GroupID
                    ).join(
                        ProcedureElement,
                        ProcedureBundle.Element_ID == ProcedureElement.ID
                    )
                    
                    if class_major:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Major == class_major)
                    
                    if class_sub:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Sub == class_sub)
                    
                    if class_detail:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Detail == class_detail)
                    
                    if class_type:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 커스텀 내 시술 검색
                if any([class_major, class_sub, class_detail, class_type]):
                    custom_query = custom_query.join(
                        ProcedureCustom,
                        ProductStandard.Custom_ID == ProcedureCustom.GroupID
                    ).join(
                        ProcedureElement,
                        ProcedureCustom.Element_ID == ProcedureElement.ID
                    )
                    
                    if class_major:
                        custom_query = custom_query.filter(ProcedureElement.Class_Major == class_major)
                    
                    if class_sub:
                        custom_query = custom_query.filter(ProcedureElement.Class_Sub == class_sub)
                    
                    if class_detail:
                        custom_query = custom_query.filter(ProcedureElement.Class_Detail == class_detail)
                    
                    if class_type:
                        custom_query = custom_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 시퀀스 내 시술 검색
                if any([class_major, class_sub, class_detail, class_type]):
                    sequence_query = sequence_query.join(
                        ProcedureSequence,
                        ProductStandard.Sequence_ID == ProcedureSequence.GroupID
                    ).join(
                        ProcedureElement,
                        ProcedureSequence.Element_ID == ProcedureElement.ID
                    )
                    
                    # class_major 필터 조건 적용
                    if class_major:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Major == class_major)
                    
                    # class_sub 필터 조건 적용
                    if class_sub:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Sub == class_sub)
                    
                    # class_detail 필터 조건 적용
                    if class_detail:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Detail == class_detail)
                    
                    # class_type 필터 조건 적용
                    if class_type:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 모든 쿼리 결과 합치기
                all_standard_products = set()
                
                # 단일시술 결과
                single_products = standard_query.all()
                for product in single_products:
                    all_standard_products.add(product.ID)
                
                # 번들 결과
                bundle_products = bundle_query.all()
                for product in bundle_products:
                    all_standard_products.add(product.ID)
                
                # 커스텀 결과
                custom_products = custom_query.all()
                for product in custom_products:
                    all_standard_products.add(product.ID)
                
                # 시퀀스 결과
                sequence_products = sequence_query.all()
                for product in sequence_products:
                    all_standard_products.add(product.ID)
                
                # 최종 Standard 상품 데이터 구성
                for product_id in all_standard_products:
                    standard_product = db.query(ProductStandard).filter(ProductStandard.ID == product_id).first()
                    if standard_product:
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
                        
                        # Info 테이블에서 상품명 가져오기
                        if standard_product.Standard_Info_ID:
                            standard_info = db.query(InfoStandard).filter(
                                InfoStandard.ID == standard_product.Standard_Info_ID
                            ).first()
                            
                            if standard_info:
                                product_data["Product_Name"] = standard_info.Product_Standard_Name
                        
                        standard_products.append(product_data)
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Standard 상품 필터링 중 오류 발생: {str(e)}"
                )
        
        # Event 상품 필터링 (Standard와 동일한 로직)
        if product_type in ["all", "event"]:
            try:
                # 기본 쿼리: ProductEvent와 ProcedureElement 조인
                event_query = db.query(ProductEvent).distinct()
                
                # 단일시술인 경우 직접 조인
                event_query = event_query.join(
                    ProcedureElement,
                    ProductEvent.Element_ID == ProcedureElement.ID
                )
                
                # class_major 필터 조건 적용
                if class_major:
                    event_query = event_query.filter(ProcedureElement.Class_Major == class_major)
                
                # class_sub 필터 조건 적용
                if class_sub:
                    event_query = event_query.filter(ProcedureElement.Class_Sub == class_sub)
                
                # class_detail 필터 조건 적용
                if class_detail:
                    event_query = event_query.filter(ProcedureElement.Class_Detail == class_detail)
                
                # class_type 필터 조건 적용
                if class_type:
                    event_query = event_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 번들/커스텀/시퀀스에 포함된 시술도 검색
                bundle_query = db.query(ProductEvent).distinct()
                custom_query = db.query(ProductEvent).distinct()
                sequence_query = db.query(ProductEvent).distinct()
                
                # 번들 내 시술 검색
                if any([class_major, class_sub, class_detail, class_type]):
                    bundle_query = bundle_query.join(
                        ProcedureBundle,
                        ProductEvent.Bundle_ID == ProcedureBundle.GroupID
                    ).join(
                        ProcedureElement,
                        ProcedureBundle.Element_ID == ProcedureElement.ID
                    )
                    
                    if class_major:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Major == class_major)
                    
                    if class_sub:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Sub == class_sub)
                    
                    if class_detail:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Detail == class_detail)
                    
                    if class_type:
                        bundle_query = bundle_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 커스텀 내 시술 검색
                if any([class_major, class_sub, class_detail, class_type]):
                    custom_query = custom_query.join(
                        ProcedureCustom,
                        ProductEvent.Custom_ID == ProcedureCustom.GroupID
                    ).join(
                        ProcedureElement,
                        ProcedureCustom.Element_ID == ProcedureElement.ID
                    )
                    
                    if class_major:
                        custom_query = custom_query.filter(ProcedureElement.Class_Major == class_major)
                    
                    if class_sub:
                        custom_query = custom_query.filter(ProcedureElement.Class_Sub == class_sub)
                    
                    if class_detail:
                        custom_query = custom_query.filter(ProcedureElement.Class_Detail == class_detail)
                    
                    if class_type:
                        custom_query = custom_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 시퀀스 내 시술 검색
                if any([class_major, class_sub, class_detail, class_type]):
                    sequence_query = sequence_query.join(
                        ProcedureSequence,
                        ProductEvent.Sequence_ID == ProcedureSequence.GroupID
                    ).join(
                        ProcedureElement,
                        ProcedureSequence.Element_ID == ProcedureElement.ID
                    )
                    
                    if class_major:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Major == class_major)
                    
                    if class_sub:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Sub == class_sub)
                    
                    if class_detail:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Detail == class_detail)
                    
                    if class_type:
                        sequence_query = sequence_query.filter(ProcedureElement.Class_Type == class_type)
                
                # 모든 쿼리 결과 합치기
                all_event_products = set()
                
                # 단일시술 결과
                single_products = event_query.all()
                for product in single_products:
                    all_event_products.add(product.ID)
                
                # 번들 결과
                bundle_products = bundle_query.all()
                for product in bundle_products:
                    all_event_products.add(product.ID)
                
                # 커스텀 결과
                custom_products = custom_query.all()
                for product in custom_products:
                    all_event_products.add(product.ID)
                
                # 시퀀스 결과
                sequence_products = sequence_query.all()
                for product in sequence_products:
                    all_event_products.add(product.ID)
                
                # 최종 Event 상품 데이터 구성
                for product_id in all_event_products:
                    event_product = db.query(ProductEvent).filter(ProductEvent.ID == product_id).first()
                    if event_product:
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
                        
                        # Info 테이블에서 상품명 가져오기
                        if event_product.Event_Info_ID:
                            event_info = db.query(InfoEvent).filter(
                                InfoEvent.ID == event_product.Event_Info_ID
                            ).first()
                            
                            if event_info:
                                event_data["Product_Name"] = event_info.Event_Name
                        
                        event_products.append(event_data)
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Event 상품 필터링 중 오류 발생: {str(e)}"
                )
        
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
        try:
            total_count = len(products)
            total_pages = (total_count + page_size - 1) // page_size
            
            # 페이지 번호 검증
            if page > total_pages and total_pages > 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"요청된 페이지({page})가 총 페이지 수({total_pages})를 초과합니다."
                )
            
            start_index = (page - 1) * page_size
            end_index = start_index + page_size
            paginated_products = products[start_index:end_index]
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"페이지네이션 처리 중 오류 발생: {str(e)}"
            )
        
        # 응답 데이터 검증
        try:
            response_data = {
                "status": "success",
                "message": f"상품 필터링 완료 (총 {total_count}개)",
                "data": paginated_products,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages
                },
                "filter_info": {
                    "class_major": class_major,
                    "class_sub": class_sub,
                    "class_detail": class_detail,
                    "class_type": class_type,
                    "product_type": product_type
                }
            }
            
            return response_data
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"응답 데이터 구성 중 오류 발생: {str(e)}"
            )
        
    except HTTPException:
        raise
    
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 파라미터 값: {str(e)}"
        )
    
    except TypeError as e:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 데이터 타입: {str(e)}"
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"상품 필터링 중 오류 발생: {str(e)}"
        )
