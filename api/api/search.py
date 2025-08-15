"""
    검색 API
    통합 검색 기능 제공 - 시술명, 분류 등 모든 필드에서 검색
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc, or_, func
from typing import List, Optional

from db.session import get_db
from db.models.product import ProductStandard, ProductEvent
from db.models.info import InfoStandard, InfoEvent
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence

search_router = APIRouter(prefix="/search", tags=["검색"])

"""
    통합 검색 API
    
    하나의 검색어로 모든 분류 필드(Name, Class_Major, Class_Sub, Class_Detail, Class_Type)를 검색함.
    해당 시술이 포함된 모든 상품(Standard/Event)을 노출시킴.
"""

@search_router.get("/products")
def search_products(
    q: str = Query(..., description="검색어 (시술명, 분류 등 모든 필드에서 검색)"),
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
        
        # 파라미터 검증: 검색어 확인
        if not q or not q.strip():
            raise HTTPException(
                status_code=400,
                detail="검색어를 입력해주세요."
            )
        
        # 검색어 정리
        search_term = q.strip()
        
        # 상품 타입별 리스트 분리
        standard_products = []
        event_products = []
        
        # Standard 상품 검색
        if product_type in ["all", "standard"]:
            try:
                # 기본 쿼리: ProductStandard와 ProcedureElement 조인
                standard_query = db.query(ProductStandard).distinct()
                
                # 단일시술인 경우 직접 조인
                standard_query = standard_query.join(
                    ProcedureElement, 
                    ProductStandard.Element_ID == ProcedureElement.ID
                )
                
                # Info 테이블과 조인 추가
                standard_query = standard_query.join(
                    InfoStandard,
                    ProductStandard.Standard_Info_ID == InfoStandard.ID
                )
                
                # 모든 분류 필드에서 검색 (개선된 검색 로직 + Info 테이블 검색)
                standard_query = standard_query.filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoStandard.Product_Standard_Name.contains(search_term),
                        InfoStandard.Product_Standard_Name.startswith(search_term),
                        InfoStandard.Product_Standard_Name.endswith(search_term),
                        func.lower(InfoStandard.Product_Standard_Name).contains(func.lower(search_term))
                    )
                )
                
                # 번들/커스텀/시퀀스에 포함된 시술도 검색
                bundle_query = db.query(ProductStandard).distinct()
                custom_query = db.query(ProductStandard).distinct()
                sequence_query = db.query(ProductStandard).distinct()
                
                # 번들 내 시술 검색 (개선된 검색 로직 + Info 테이블 검색)
                bundle_query = bundle_query.join(
                    ProcedureBundle, 
                    ProductStandard.Bundle_ID == ProcedureBundle.GroupID
                ).join(
                    ProcedureElement,
                    ProcedureBundle.Element_ID == ProcedureElement.ID
                ).join(
                    InfoStandard,
                    ProductStandard.Standard_Info_ID == InfoStandard.ID
                ).filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoStandard.Product_Standard_Name.contains(search_term),
                        InfoStandard.Product_Standard_Name.startswith(search_term),
                        InfoStandard.Product_Standard_Name.endswith(search_term),
                        func.lower(InfoStandard.Product_Standard_Name).contains(func.lower(search_term))
                    )
                )
                
                # 커스텀 내 시술 검색 (개선된 검색 로직 + Info 테이블 검색)
                custom_query = custom_query.join(
                    ProcedureCustom,
                    ProductStandard.Custom_ID == ProcedureCustom.GroupID
                ).join(
                    ProcedureElement,
                    ProcedureCustom.Element_ID == ProcedureElement.ID
                ).join(
                    InfoStandard,
                    ProductStandard.Standard_Info_ID == InfoStandard.ID
                ).filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoStandard.Product_Standard_Name.contains(search_term),
                        InfoStandard.Product_Standard_Name.startswith(search_term),
                        InfoStandard.Product_Standard_Name.endswith(search_term),
                        func.lower(InfoStandard.Product_Standard_Name).contains(func.lower(search_term))
                    )
                )
                
                # 시퀀스 내 시술 검색 (개선된 검색 로직 + Info 테이블 검색)
                sequence_query = sequence_query.join(
                    ProcedureSequence,
                    ProductStandard.Sequence_ID == ProcedureSequence.GroupID
                ).join(
                    ProcedureElement,
                    ProcedureSequence.Element_ID == ProcedureElement.ID
                ).join(
                    InfoStandard,
                    ProductStandard.Standard_Info_ID == InfoStandard.ID
                ).filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoStandard.Product_Standard_Name.contains(search_term),
                        InfoStandard.Product_Standard_Name.startswith(search_term),
                        InfoStandard.Product_Standard_Name.endswith(search_term),
                        func.lower(InfoStandard.Product_Standard_Name).contains(func.lower(search_term))
                    )
                )
                
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
                            "Sell_Price": standard_product.Sell_Price,
                            "Original_Price": standard_product.Original_Price,
                            "Discount_Rate": standard_product.Discount_Rate,
                            "Product_Name": None,
                            "elements": []  # Element 정보 추가
                        }
                        
                        # Info 테이블에서 상품명 가져오기
                        if standard_product.Standard_Info_ID:
                            standard_info = db.query(InfoStandard).filter(
                                InfoStandard.ID == standard_product.Standard_Info_ID
                            ).first()
                            
                            if standard_info:
                                product_data["Product_Name"] = standard_info.Product_Standard_Name
                        
                        # Package_Type별 Element Class_Type만 추가
                        if standard_product.Package_Type == "단일시술" and standard_product.Element_ID:
                            element = db.query(ProcedureElement).filter(
                                ProcedureElement.ID == standard_product.Element_ID
                            ).first()
                            if element and element.Class_Type:
                                product_data["elements"].append(element.Class_Type)
                        
                        elif standard_product.Package_Type == "번들" and standard_product.Bundle_ID:
                            bundle_elements = db.query(ProcedureElement.Class_Type).join(
                                ProcedureBundle, ProcedureElement.ID == ProcedureBundle.Element_ID
                            ).filter(
                                ProcedureBundle.GroupID == standard_product.Bundle_ID,
                                ProcedureElement.Class_Type.isnot(None)
                            ).all()
                            
                            for element in bundle_elements:
                                if element.Class_Type:
                                    product_data["elements"].append(element.Class_Type)
                        
                        elif standard_product.Package_Type == "커스텀" and standard_product.Custom_ID:
                            custom_elements = db.query(ProcedureElement.Class_Type).join(
                                ProcedureCustom, ProcedureElement.ID == ProcedureCustom.Element_ID
                            ).filter(
                                ProcedureCustom.GroupID == standard_product.Custom_ID,
                                ProcedureElement.Class_Type.isnot(None)
                            ).all()
                            
                            for element in custom_elements:
                                if element.Class_Type:
                                    product_data["elements"].append(element.Class_Type)
                        
                        elif standard_product.Package_Type == "시퀀스" and standard_product.Sequence_ID:
                            sequence_elements = db.query(ProcedureElement.Class_Type).join(
                                ProcedureSequence, ProcedureElement.ID == ProcedureSequence.Element_ID
                            ).filter(
                                ProcedureSequence.GroupID == standard_product.Sequence_ID,
                                ProcedureElement.Class_Type.isnot(None)
                            ).all()
                            
                            for element in sequence_elements:
                                if element.Class_Type:
                                    product_data["elements"].append(element.Class_Type)
                        
                        standard_products.append(product_data)
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Standard 상품 검색 중 오류 발생: {str(e)}"
                )
        
        # Event 상품 검색 (Standard와 동일한 로직)
        if product_type in ["all", "event"]:
            try:
                # 기본 쿼리: ProductEvent와 ProcedureElement 조인
                event_query = db.query(ProductEvent).distinct()
                
                # 단일시술인 경우 직접 조인 + Info 테이블 조인
                event_query = event_query.join(
                    ProcedureElement,
                    ProductEvent.Element_ID == ProcedureElement.ID
                ).join(
                    InfoEvent,
                    ProductEvent.Event_Info_ID == InfoEvent.ID
                )
                
                # 모든 분류 필드에서 검색 (개선된 검색 로직 + Info 테이블 검색)
                event_query = event_query.filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoEvent.Event_Name.contains(search_term),
                        InfoEvent.Event_Name.startswith(search_term),
                        InfoEvent.Event_Name.endswith(search_term),
                        func.lower(InfoEvent.Event_Name).contains(func.lower(search_term))
                    )
                )
                
                # 번들/커스텀/시퀀스에 포함된 시술도 검색
                bundle_query = db.query(ProductEvent).distinct()
                custom_query = db.query(ProductEvent).distinct()
                sequence_query = db.query(ProductEvent).distinct()
                
                # 번들 내 시술 검색 (개선된 검색 로직 + Info 테이블 검색)
                bundle_query = bundle_query.join(
                    ProcedureBundle,
                    ProductEvent.Bundle_ID == ProcedureBundle.GroupID
                ).join(
                    ProcedureElement,
                    ProcedureBundle.Element_ID == ProcedureElement.ID
                ).join(
                    InfoEvent,
                    ProductEvent.Event_Info_ID == InfoEvent.ID
                ).filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoEvent.Event_Name.contains(search_term),
                        InfoEvent.Event_Name.startswith(search_term),
                        InfoEvent.Event_Name.endswith(search_term),
                        func.lower(InfoEvent.Event_Name).contains(func.lower(search_term))
                    )
                )
                
                # 커스텀 내 시술 검색 (개선된 검색 로직 + Info 테이블 검색)
                custom_query = custom_query.join(
                    ProcedureCustom,
                    ProductEvent.Custom_ID == ProcedureCustom.GroupID
                ).join(
                    ProcedureElement,
                    ProcedureCustom.Element_ID == ProcedureElement.ID
                ).join(
                    InfoEvent,
                    ProductEvent.Event_Info_ID == InfoEvent.ID
                ).filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoEvent.Event_Name.contains(search_term),
                        InfoEvent.Event_Name.startswith(search_term),
                        InfoEvent.Event_Name.endswith(search_term),
                        func.lower(InfoEvent.Event_Name).contains(func.lower(search_term))
                    )
                )
                
                # 시퀀스 내 시술 검색 (개선된 검색 로직 + Info 테이블 검색)
                sequence_query = sequence_query.join(
                    ProcedureSequence,
                    ProductEvent.Sequence_ID == ProcedureSequence.GroupID
                ).join(
                    ProcedureElement,
                    ProcedureSequence.Element_ID == ProcedureElement.ID
                ).join(
                    InfoEvent,
                    ProductEvent.Event_Info_ID == InfoEvent.ID
                ).filter(
                    or_(
                        # ProcedureElement 필드 검색 (기존)
                        ProcedureElement.Name.contains(search_term),
                        ProcedureElement.Class_Major == search_term,
                        ProcedureElement.Class_Sub == search_term,
                        ProcedureElement.Class_Detail == search_term,
                        ProcedureElement.Class_Type == search_term,
                        # 접두사 검색 (새로 추가)
                        ProcedureElement.Name.startswith(search_term),
                        ProcedureElement.Class_Major.startswith(search_term),
                        ProcedureElement.Class_Sub.startswith(search_term),
                        ProcedureElement.Class_Detail.startswith(search_term),
                        ProcedureElement.Class_Type.startswith(search_term),
                        # 접미사 검색 (새로 추가)
                        ProcedureElement.Name.endswith(search_term),
                        ProcedureElement.Class_Major.endswith(search_term),
                        ProcedureElement.Class_Sub.endswith(search_term),
                        ProcedureElement.Class_Detail.endswith(search_term),
                        ProcedureElement.Class_Type.endswith(search_term),
                        # 대소문자 무시 검색 (새로 추가)
                        func.lower(ProcedureElement.Name).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Major).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Sub).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Detail).contains(func.lower(search_term)),
                        func.lower(ProcedureElement.Class_Type).contains(func.lower(search_term)),
                        # Info 테이블 상품명 검색 (새로 추가)
                        InfoEvent.Event_Name.contains(search_term),
                        InfoEvent.Event_Name.startswith(search_term),
                        InfoEvent.Event_Name.endswith(search_term),
                        func.lower(InfoEvent.Event_Name).contains(func.lower(search_term))
                    )
                )
                
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
                            "Sell_Price": event_product.Sell_Price,
                            "Original_Price": event_product.Original_Price,
                            "Discount_Rate": event_product.Discount_Rate,
                            "Product_Name": None,
                            "elements": []  # Element 정보 추가
                        }
                        
                        # Info 테이블에서 상품명 가져오기
                        if event_product.Event_Info_ID:
                            event_info = db.query(InfoEvent).filter(
                                InfoEvent.ID == event_product.Event_Info_ID
                            ).first()
                            
                            if event_info:
                                event_data["Product_Name"] = event_info.Event_Name
                        
                        # Package_Type별 Element Class_Type만 추가
                        if event_product.Package_Type == "단일시술" and event_product.Element_ID:
                            element = db.query(ProcedureElement).filter(
                                ProcedureElement.ID == event_product.Element_ID
                            ).first()
                            if element and element.Class_Type:
                                event_data["elements"].append(element.Class_Type)
                        
                        elif event_product.Package_Type == "번들" and event_product.Bundle_ID:
                            bundle_elements = db.query(ProcedureElement.Class_Type).join(
                                ProcedureBundle, ProcedureElement.ID == ProcedureBundle.Element_ID
                            ).filter(
                                ProcedureBundle.GroupID == event_product.Bundle_ID,
                                ProcedureElement.Class_Type.isnot(None)
                            ).all()
                            
                            for element in bundle_elements:
                                if element.Class_Type:
                                    event_data["elements"].append(element.Class_Type)
                        
                        elif event_product.Package_Type == "커스텀" and event_product.Custom_ID:
                            custom_elements = db.query(ProcedureElement.Class_Type).join(
                                ProcedureCustom, ProcedureElement.ID == ProcedureCustom.Element_ID
                            ).filter(
                                ProcedureCustom.GroupID == event_product.Custom_ID,
                                ProcedureElement.Class_Type.isnot(None)
                            ).all()
                            
                            for element in custom_elements:
                                if element.Class_Type:
                                    event_data["elements"].append(element.Class_Type)
                        
                        elif event_product.Package_Type == "시퀀스" and event_product.Sequence_ID:
                            sequence_elements = db.query(ProcedureElement.Class_Type).join(
                                ProcedureSequence, ProcedureElement.ID == ProcedureSequence.Element_ID
                            ).filter(
                                ProcedureSequence.GroupID == event_product.Sequence_ID,
                                ProcedureElement.Class_Type.isnot(None)
                            ).all()
                            
                            for element in sequence_elements:
                                if element.Class_Type:
                                    event_data["elements"].append(element.Class_Type)
                        
                        event_products.append(event_data)
                        
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Event 상품 검색 중 오류 발생: {str(e)}"
                )
        
        # 요청된 상품 타입에 따라 최종 결과 구성
        if product_type == "standard":
            products = standard_products
        
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
        
        # 응답 데이터 구성
        try:
            response_data = {
                "status": "success",
                "message": f"검색 완료 (총 {total_count}개)",
                "data": paginated_products,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total_count": total_count,
                    "total_pages": total_pages
                },
                "search_info": {
                    "query": search_term,
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
        # 로그 기록 (실제 운영환경에서는 로깅 라이브러리 사용)
        print(f"검색 API 오류: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"상품 검색 중 오류 발생: {str(e)}"
        )
