"""
    조회 API
    프론트엔드 요구사항에 맞는 데이터 조회 기능 제공
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc

from db.session import get_db
from db import (
    InfoEvent, InfoStandard,
    ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence,
    ProductEvent, ProductStandard
)

read_router = APIRouter(
    prefix="/read",
    tags=["Read"]
)

"""
    Product 목록 조회
    
    Product_Standard와 Product_Event 테이블의 기본 정보를 조회합니다.
    프론트엔드에서 상품 목록을 띄우기 위한 API입니다.
"""

@read_router.get("/products")
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
            # Product_Standard 테이블에서 상품 목록을 조회
            standard_products = db.query(ProductStandard).order_by(
                ProductStandard.Package_Type, ProductStandard.ID
            ).all()
            
            for standard_product in standard_products:
                product_data = {
                    "ID": standard_product.ID,
                    "Product_Type": "standard",
                    "Package_Type": standard_product.Package_Type,
                    "Sell_Price": standard_product.Sell_Price,
                    "Original_Price": standard_product.Original_Price,
                    "Standard_Start_Date": standard_product.Standard_Start_Date,
                    "Standard_End_Date": standard_product.Standard_End_Date,
                    "Validity_Period": standard_product.Validity_Period
                }
                
                # Standard_Info 정보 추가
                if standard_product.Standard_Info_ID:
                    standard_info = db.query(InfoStandard).filter(
                        InfoStandard.ID == standard_product.Standard_Info_ID
                    ).first()
                    
                    if standard_info:
                        product_data["Product_Name"] = standard_info.Product_Standard_Name
                        product_data["Product_Description"] = standard_info.Product_Standard_Description
                        product_data["Precautions"] = standard_info.Precautions
                    else:
                        # Info 테이블에서 정보를 찾을 수 없는 경우 (경고만, 에러는 아님)
                        product_data["Product_Name"] = None
                        product_data["Product_Description"] = None
                        product_data["Precautions"] = None
                else:
                    # Standard_Info_ID가 없는 경우
                    product_data["Product_Name"] = None
                    product_data["Product_Description"] = None
                    product_data["Precautions"] = None
                
                # 시술 이름과 Class_Type 추가
                procedure_names = []
                class_types = []
                
                # 1. 단일 시술 (Element_ID)
                if standard_product.Element_ID:
                    element = db.query(ProcedureElement).filter(
                        ProcedureElement.ID == standard_product.Element_ID
                    ).first()
                    if element:
                        procedure_names.append(element.Name)
                        if element.Class_Type:
                            class_types.append(element.Class_Type)
                
                # 2. 시술 묶음 (Bundle_ID)
                elif standard_product.Bundle_ID:
                    bundle_elements = db.query(ProcedureElement).join(
                        ProcedureBundle, ProcedureElement.ID == ProcedureBundle.Element_ID
                    ).filter(
                        ProcedureBundle.GroupID == standard_product.Bundle_ID
                    ).all()
                    for elem in bundle_elements:
                        procedure_names.append(elem.Name)
                        if elem.Class_Type:
                            class_types.append(elem.Class_Type)
                
                # 3. 커스텀 (Custom_ID)
                elif standard_product.Custom_ID:
                    custom_elements = db.query(ProcedureElement).join(
                        ProcedureCustom, ProcedureElement.ID == ProcedureCustom.Element_ID
                    ).filter(
                        ProcedureCustom.GroupID == standard_product.Custom_ID
                    ).all()
                    for elem in custom_elements:
                        procedure_names.append(elem.Name)
                        if elem.Class_Type:
                            class_types.append(elem.Class_Type)
                
                # 4. 시퀀스 (Sequence_ID)
                elif standard_product.Sequence_ID:
                    sequence_elements = db.query(ProcedureElement).join(
                        ProcedureSequence, ProcedureElement.ID == ProcedureSequence.Element_ID
                    ).filter(
                        ProcedureSequence.GroupID == standard_product.Sequence_ID
                    ).all()
                    for elem in sequence_elements:
                        procedure_names.append(elem.Name)
                        if elem.Class_Type:
                            class_types.append(elem.Class_Type)
                
                # 시술 이름과 Class_Type을 응답에 추가
                product_data["procedure_names"] = procedure_names
                product_data["procedure_count"] = len(procedure_names)
                product_data["class_types"] = list(set(class_types))  # 중복 제거
                product_data["class_type_count"] = len(set(class_types))
                
                # 상품 목록에 추가 (Standard 상품)
                products.append(product_data)
        
        # Product_Event 조회 (Event_Start_Date 기준 최신순)
        if product_type in ["all", "event"]:
            event_products = db.query(ProductEvent).order_by(
                desc(ProductEvent.Event_Start_Date)
            ).all()
            
            for event_product in event_products:
                event_data = {
                    "ID": event_product.ID,
                    "Product_Type": "event",
                    "Package_Type": event_product.Package_Type,
                    "Sell_Price": event_product.Sell_Price,
                    "Original_Price": event_product.Original_Price,
                    "Event_Start_Date": event_product.Event_Start_Date,
                    "Event_End_Date": event_product.Event_End_Date,
                    "Validity_Period": event_product.Validity_Period
                }
                
                # Event_Info 정보 추가
                if event_product.Event_Info_ID:
                    event_info = db.query(InfoEvent).filter(
                        InfoEvent.ID == event_product.Event_Info_ID
                    ).first()
                    
                    if event_info:
                        event_data["Product_Name"] = event_info.Event_Name
                        event_data["Product_Description"] = event_info.Event_Description
                        event_data["Precautions"] = event_info.Precautions
                    else:
                        # Info 테이블에서 정보를 찾을 수 없는 경우 (경고만, 에러는 아님)
                        event_data["Product_Name"] = None
                        event_data["Product_Description"] = None
                        event_data["Precautions"] = None
                else:
                    # Event_Info_ID가 없는 경우
                    event_data["Product_Name"] = None
                    event_data["Product_Description"] = None
                    event_data["Precautions"] = None
                
                # 시술 이름과 Class_Type 추가 (Event 상품도 동일한 로직)
                procedure_names = []
                class_types = []
                
                # 1. 단일 시술 (Element_ID)
                if event_product.Element_ID:
                    element = db.query(ProcedureElement).filter(
                        ProcedureElement.ID == event_product.Element_ID
                    ).first()
                    if element:
                        procedure_names.append(element.Name)
                        if element.Class_Type:
                            class_types.append(element.Class_Type)
                
                # 2. 시술 묶음 (Bundle_ID)
                elif event_product.Bundle_ID:
                    bundle_elements = db.query(ProcedureElement).join(
                        ProcedureBundle, ProcedureElement.ID == ProcedureBundle.Element_ID
                    ).filter(
                        ProcedureBundle.GroupID == event_product.Bundle_ID
                    ).all()
                    for elem in bundle_elements:
                        procedure_names.append(elem.Name)
                        if elem.Class_Type:
                            class_types.append(elem.Class_Type)
                
                # 3. 커스텀 (Custom_ID)
                elif event_product.Custom_ID:
                    custom_elements = db.query(ProcedureElement).join(
                        ProcedureCustom, ProcedureElement.ID == ProcedureCustom.Element_ID
                    ).filter(
                        ProcedureCustom.GroupID == event_product.Custom_ID
                    ).all()
                    for elem in custom_elements:
                        procedure_names.append(elem.Name)
                        if elem.Class_Type:
                            class_types.append(elem.Class_Type)
                
                # 4. 시퀀스 (Sequence_ID)
                elif event_product.Sequence_ID:
                    sequence_elements = db.query(ProcedureElement).join(
                        ProcedureSequence, ProcedureElement.ID == ProcedureSequence.Element_ID
                    ).filter(
                        ProcedureSequence.GroupID == event_product.Sequence_ID
                    ).all()
                    for elem in sequence_elements:
                        procedure_names.append(elem.Name)
                        if elem.Class_Type:
                            class_types.append(elem.Class_Type)
                
                # 시술 이름과 Class_Type을 응답에 추가
                event_data["procedure_names"] = procedure_names
                event_data["procedure_count"] = len(procedure_names)
                event_data["class_types"] = list(set(class_types))  # 중복 제거
                event_data["class_type_count"] = len(set(class_types))
                
                # 상품 목록에 추가 (Event 상품)
                products.append(event_data)
        
        # 페이지네이션
        total_count = len(products)
        offset = (page - 1) * page_size
        paginated_products = products[offset:offset + page_size]
        
        return {
            "status": "success",
            "message": "상품 목록 조회 완료",
            "data": paginated_products,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_count": total_count,
                "total_pages": (total_count + page_size - 1) // page_size
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상품 목록 조회 중 오류 발생: {str(e)}"
        )


# Product 상세 조회
"""
    Product 상세 조회

    클릭된 상품의 상세 정보를 조회한다.
    해당 '상품'에 속한 모든 Element, Bundle, Sequence 정보를 전부 조회한다.
"""

@read_router.get("/products/{product_id}")
def get_product_detail(
    product_id: int,
    product_type: str = Query(..., description="상품 타입 (standard/event)"),
    db: Session = Depends(get_db)
):
    try:
        # Standard 상품 조회
        if product_type == "standard":
            product = db.query(ProductStandard).filter(ProductStandard.ID == product_id).first()
            
            if not product: # Product_Standard애서 상품을 찾을 수 없을 경우
                raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
        
        # Event 상품 조회
        elif product_type == "event":
            product = db.query(ProductEvent).filter(ProductEvent.ID == product_id).first()
            
            if not product: # Product_Event에서 상품을 찾을 수 없을 경우
                raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
        
        # 상품 타입이 잘못되었을 경우
        else:
            raise HTTPException(status_code=400, detail="잘못된 상품 타입입니다.")
        
        # 상품 기본 정보(Product)를 Python Dictionary 형태로 저장: 실데이터가 Key에 저장되는 구조
        product_data = {
            "ID": product.ID,                                   # 상품 ID
            "Product_Type": product_type,                       # 상품의 기본 타입 (Standard, Event)
            "Package_Type": product.Package_Type,               # 상품의 패키지 타입 (단일시술, 번들, 커스텀, 시퀀스)
            "Element_ID": product.Element_ID,                   # 단일시술 ID
            "Bundle_ID": product.Bundle_ID,                     # 번들 ID
            "Custom_ID": product.Custom_ID,                     # 커스텀 ID
            "Sequence_ID": product.Sequence_ID,                 # 시퀀스 ID
            "Sell_Price": product.Sell_Price,                   # 판매 가격 (정상가에 할인율이 적용된 실판매가)
            "Original_Price": product.Original_Price,           # 정상가 (원가가 아닌, 할인율에 정당성을 부여하기 위한 가격)
            "Discount_Rate": product.Discount_Rate,             # 할인율 (정상가에서 Discount_Rate만큼 할인이 되서 Sell_Price가 되는 구조)
            "Validity_Period": product.Validity_Period,         # 상품 유효기간
            "VAT": product.VAT,                                 # 부가세
            "Covered_Type": product.Covered_Type,               # 급여분류 (급여/비급여)
            "Taxable_Type": product.Taxable_Type                # 과세분류 (과세/면세)
        }
        
        # Product_Type에 따른 상품 노출 기간 (Standard, Event)
        if product_type == "standard":
            product_data["Standard_Start_Date"] = product.Standard_Start_Date       # 상품 노출 시작일
            product_data["Standard_End_Date"] = product.Standard_End_Date           # 상품 노출 종료일
            
            # Standard 상품명과 설명 추가
            if product.Standard_Info_ID:
                standard_info = db.query(InfoStandard).filter(
                    InfoStandard.ID == product.Standard_Info_ID
                ).first()
                
                if standard_info:
                    product_data["Product_Name"] = standard_info.Product_Standard_Name
                    product_data["Product_Description"] = standard_info.Product_Standard_Description
                    product_data["Precautions"] = standard_info.Precautions
                else:
                    product_data["Product_Name"] = None
                    product_data["Product_Description"] = None
                    product_data["Precautions"] = None
            else:
                product_data["Product_Name"] = None
                product_data["Product_Description"] = None
                product_data["Precautions"] = None
            
        
        elif product_type == "event":
            product_data["Event_Start_Date"] = product.Event_Start_Date             # 이벤트 시작일
            product_data["Event_End_Date"] = product.Event_End_Date                 # 이벤트 종료일
            
            # Event 상품명과 설명 추가
            if hasattr(product, 'Event_Info_ID') and product.Event_Info_ID:
                event_info = db.query(InfoEvent).filter(
                    InfoEvent.ID == product.Event_Info_ID
                ).first()
                
                if event_info:
                    product_data["Product_Name"] = event_info.Event_Name
                    product_data["Product_Description"] = event_info.Event_Description
                    product_data["Precautions"] = event_info.Precautions
                else:
                    product_data["Product_Name"] = None
                    product_data["Product_Description"] = None
                    product_data["Precautions"] = None
            else:
                product_data["Product_Name"] = None
                product_data["Product_Description"] = None
                product_data["Precautions"] = None
        
        ### ==== Package_Type별 상세 정보 추가 ==== ###
        
        # Package_Type이 '단일시술'일 경우 Procedure_Element 조회
        if product.Package_Type == "단일시술":
  
            if product.Element_ID:  # 단일시술 ID가 있는 경우
                element = db.query(ProcedureElement).filter(
                    ProcedureElement.ID == product.Element_ID
                ).first()
                
                # 단일시술에 포함된 데이터들 저장
                if element:
                    product_data["element_details"] = {
                        "Class_Major": element.Class_Major,
                        "Class_Sub": element.Class_Sub,
                        "Class_Detail": element.Class_Detail,
                        "Class_Type": element.Class_Type,
                        "Name": element.Name,
                        "Cost_Time": element.Cost_Time,
                        "Plan_State": element.Plan_State,
                        "Plan_Count": element.Plan_Count,
                        "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                        "Element_Cost": element.Price  # 단일시술 가격 정보 추가
                    }
                
                else:   # 단일시술에 포함된 데이터들을 찾을 수 없을 경우 (예외처리)
                    raise HTTPException(status_code=404, detail=f"시술 정보를 찾을 수 없습니다. (Element_ID: {product.Element_ID})")
            
            else:   # 단일시술 ID가 없는 경우 (예외처리)
                raise HTTPException(status_code=404, detail="단일시술을 찾을 수 없습니다.")
        
        # Package_Type이 '번들'일 경우 Procedure_Bundle 조회
        elif product.Package_Type == "번들":
            
            if product.Bundle_ID:  # 번들 ID가 있는 경우: 번들 정보 + 번들에 포함된 모든 Element들
                bundle_list = db.query(ProcedureBundle).filter(
                    ProcedureBundle.GroupID == product.Bundle_ID
                ).order_by(ProcedureBundle.ID).all()  # 번들 ID (GroupID)를 기준으로 정렬
                
                if not bundle_list:
                    raise HTTPException(status_code=404, detail="번들 정보를 찾을 수 없습니다.")
                
                bundle_details = []     # 번들에 포함된 모든 Element들의 정보를 저장하는 리스트
                bundle_name = None      # 번들의 이름을 저장하는 변수
                
                # 번들에 포함된 모든 Element들을 순회
                for bundle_item in bundle_list:
                    # GroupID + ID의 구조에서 ID가 1인 경우 번들 이름도 저장
                    if bundle_item.ID == 1:
                        bundle_name = bundle_item.Name
                    
                        # ID가 1인 행에서 bundle 이름을 저장하고, 포함된 Element ID 확인 후 해당 Element의 정보도 저장
                        if bundle_item.Element_ID:
                            element = db.query(ProcedureElement).filter(
                                ProcedureElement.ID == bundle_item.Element_ID
                            ).first()
                            
                            if element:
                                bundle_details.append({
                                    "ID": bundle_item.ID,
                                    "Element_ID": bundle_item.Element_ID,
                                    "Element_Cost": bundle_item.Element_Cost,
                                    "Element_Info": {
                                        "Class_Major": element.Class_Major,
                                        "Class_Sub": element.Class_Sub,
                                        "Class_Detail": element.Class_Detail,
                                        "Class_Type": element.Class_Type,
                                        "Name": element.Name,
                                        "Cost_Time": element.Cost_Time,
                                        "Plan_State": element.Plan_State,
                                        "Plan_Count": element.Plan_Count,
                                        "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                                        "Element_Cost": element.Price  # 번들 내 Element 가격 정보 추가
                                    }
                                })
                            
                            else:   # 번들에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                                raise HTTPException(status_code=404, detail=f"번들 내 시술 정보를 찾을 수 없습니다. (Element_ID: {bundle_item.Element_ID})")
                    
                    # ID=2~n인 경우: 번들에 포함된 다른 Element들의 정보도 확인 후 저장
                    elif bundle_item.Element_ID:
                        element = db.query(ProcedureElement).filter(
                            ProcedureElement.ID == bundle_item.Element_ID
                        ).first()
                        
                        if element:
                            bundle_details.append({
                                "ID": bundle_item.ID,
                                "Element_ID": bundle_item.Element_ID,
                                "Element_Cost": bundle_item.Element_Cost,
                                "Element_Info": {
                                    "Class_Major": element.Class_Major,
                                    "Class_Sub": element.Class_Sub,
                                    "Class_Detail": element.Class_Detail,
                                    "Class_Type": element.Class_Type,
                                    "Name": element.Name,
                                    "Cost_Time": element.Cost_Time,
                                    "Plan_State": element.Plan_State,
                                    "Plan_Count": element.Plan_Count,
                                    "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                                    "Element_Cost": element.Price  # 번들 내 Element 가격 정보 추가
                                }
                            })
                        
                        else:   # 번들에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                            raise HTTPException(status_code=404, detail=f"번들 내 시술 정보를 찾을 수 없습니다. (Element_ID: {bundle_item.Element_ID})")
                
                # 번들 이름 저장
                if bundle_name:
                    product_data["bundle_name"] = bundle_name
                
                else:   # 번들 이름을 찾을 수 없을 경우 (예외처리)
                    raise HTTPException(status_code=404, detail="번들 이름을 찾을 수 없습니다.")
                
                # 번들에 포함된 모든 Element들의 정보를 저장
                if bundle_details:
                    product_data["bundle_details"] = bundle_details
                
                else:   # 번들에 포함된 데이터들을 찾을 수 없을 경우 (예외처리)
                    raise HTTPException(status_code=404, detail="번들에 포함된 시술 정보가 없습니다.")
            else:
                raise HTTPException(status_code=404, detail="번들 ID가 없습니다.")
        
        # Package_Type이 '커스텀'일 경우 Procedure_Custom 조회
        elif product.Package_Type == "커스텀":
            
            if product.Custom_ID:   # 커스텀 ID가 있는 경우
                custom_list = db.query(ProcedureCustom).filter(
                    ProcedureCustom.GroupID == product.Custom_ID
                ).all()
                
                if not custom_list:
                    raise HTTPException(status_code=404, detail="커스텀 정보를 찾을 수 없습니다.")
                
                custom_details = []   # 커스텀에 포함된 모든 Element들의 정보를 저장하는 리스트
                custom_name = None    # 커스텀 이름을 저장하는 변수
                
                # 커스텀에 포함된 모든 Element들을 순회
                for custom_item in custom_list:
                    # GroupID + ID의 구조에서 ID가 1인 경우 커스텀 이름도 저장
                    if custom_item.ID == 1:
                        custom_name = custom_item.Name  # 커스텀 이름 저장
                        
                        # ID가 1인 행에서 커스텀 이름을 저장하고, 포함된 Element ID 확인 후 해당 Element의 정보도 저장
                        if custom_item.Element_ID:
                            element = db.query(ProcedureElement).filter(
                                ProcedureElement.ID == custom_item.Element_ID
                            ).first()

                            if element:
                                custom_details.append({
                                    "ID": custom_item.ID,
                                    "Element_ID": custom_item.Element_ID,
                                    "Custom_Count": custom_item.Custom_Count,      # 각 Element별 Custom_Count
                                    "Element_Limit": custom_item.Element_Limit,    # 각 Element별 Element_Limit
                                    "Element_Cost": custom_item.Element_Cost,
                                    "Element_Info": {
                                        "Class_Major": element.Class_Major,
                                        "Class_Sub": element.Class_Sub,
                                        "Class_Detail": element.Class_Detail,
                                        "Class_Type": element.Class_Type,
                                        "Name": element.Name,
                                        "Cost_Time": element.Cost_Time,
                                        "Plan_State": element.Plan_State,
                                        "Plan_Count": element.Plan_Count,
                                        "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                                        "Element_Cost": element.Price  # 커스텀 내 Element 가격 정보 추가
                                    }
                                })
                            
                            else:   # 커스텀에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                                raise HTTPException(status_code=404, detail=f"커스텀 내 시술 정보를 찾을 수 없습니다. (Element_ID: {custom_item.Element_ID})")
                    
                    # ID=2~n인 경우: 커스텀에 포함된 다른 Element들의 정보도 확인 후 저장
                    elif custom_item.Element_ID:
                        element = db.query(ProcedureElement).filter(
                            ProcedureElement.ID == custom_item.Element_ID
                        ).first()
                        
                        if element:
                            custom_details.append({
                                "ID": custom_item.ID,
                                "Element_ID": custom_item.Element_ID,
                                "Custom_Count": custom_item.Custom_Count,      # 각 Element별 Custom_Count
                                "Element_Limit": custom_item.Element_Limit,   # 각 Element별 Element_Limit
                                "Element_Cost": custom_item.Element_Cost,
                                "Element_Info": {
                                    "Class_Major": element.Class_Major,
                                    "Class_Sub": element.Class_Sub,
                                    "Class_Detail": element.Class_Detail,
                                    "Class_Type": element.Class_Type,
                                    "Name": element.Name,
                                    "Cost_Time": element.Cost_Time,
                                    "Plan_State": element.Plan_State,
                                    "Plan_Count": element.Plan_Count,
                                    "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                                    "Element_Cost": element.Price  # 커스텀 내 Element 가격 정보 추가
                                }
                            })
                        
                        else:   # 커스텀에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                            raise HTTPException(status_code=404, detail=f"커스텀 내 시술 정보를 찾을 수 없습니다. (Element_ID: {custom_item.Element_ID})")
                
                # 커스텀 이름 저장
                if custom_name:
                    product_data["custom_name"] = custom_name
                    
                else:   # 커스텀 이름을 찾을 수 없을 경우 (예외처리)
                    raise HTTPException(status_code=404, detail="커스텀 이름을 찾을 수 없습니다.")
                
                # 커스텀에 포함된 모든 Element들의 정보를 저장
                if custom_details:
                    product_data["custom_details"] = custom_details
                
                else:   # 커스텀에 포함된 데이터들을 찾을 수 없을 경우 (예외처리)
                    raise HTTPException(status_code=404, detail="커스텀에 포함된 시술 정보가 없습니다.")
            else:
                raise HTTPException(status_code=404, detail="커스텀 ID가 없습니다.")
        
        # Package_Type이 '시퀀스'일 경우 Procedure_Sequence 조회
        elif product.Package_Type == "시퀀스":

            if product.Sequence_ID:   # 시퀀스 ID가 있는 경우
                sequence_list = db.query(ProcedureSequence).filter(
                    ProcedureSequence.GroupID == product.Sequence_ID
                ).order_by(ProcedureSequence.Step_Num).all()
                
                if not sequence_list:
                    raise HTTPException(status_code=404, detail="시퀀스 정보를 찾을 수 없습니다.")
                
                sequence_details = []   # 시퀀스에 포함된 모든 Element들의 정보를 저장하는 리스트
                
                # 시퀀스에 포함된 모든 Element들을 순회
                for sequence_item in sequence_list:
                    # Step_Num과 elements 정보를 저장하는 딕셔너리
                    step_details = {
                        "Step_Num": sequence_item.Step_Num,
                        "elements": []
                    }
                    
                    # Element_ID가 있는 경우 (단일 Element)
                    if sequence_item.Element_ID:
                        element = db.query(ProcedureElement).filter(
                            ProcedureElement.ID == sequence_item.Element_ID
                        ).first()

                        if element:
                            step_details["elements"].append({
                                "Class_Major": element.Class_Major,
                                "Class_Sub": element.Class_Sub,
                                "Class_Detail": element.Class_Detail,
                                "Class_Type": element.Class_Type,
                                "Name": element.Name,
                                "Cost_Time": element.Cost_Time,
                                "Plan_State": element.Plan_State,
                                "Plan_Count": element.Plan_Count,
                                "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                                "Element_Cost": element.Price  # 단일 Element의 가격 정보 추가
                            })
                        
                        else:   # 시퀀스에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                            raise HTTPException(status_code=404, detail=f"시퀀스 내 시술 정보를 찾을 수 없습니다. (Element_ID: {sequence_item.Element_ID})")
                    
                    # Bundle_ID가 있는 경우 (번들 - Element 단위로 분할)
                    elif sequence_item.Bundle_ID:
                        bundle_list = db.query(ProcedureBundle).filter(
                            ProcedureBundle.GroupID == sequence_item.Bundle_ID
                        ).all()
                        
                        if not bundle_list:
                            raise HTTPException(status_code=404, detail=f"시퀀스 내 번들 정보를 찾을 수 없습니다. (Bundle_ID: {sequence_item.Bundle_ID})")
                        
                        for bundle_item in bundle_list:
                            if bundle_item.Element_ID:
                                element = db.query(ProcedureElement).filter(
                                    ProcedureElement.ID == bundle_item.Element_ID
                                ).first()
                                
                                if element:
                                    step_details["elements"].append({
                                        "Class_Major": element.Class_Major,
                                        "Class_Sub": element.Class_Sub,
                                        "Class_Detail": element.Class_Detail,
                                        "Class_Type": element.Class_Type,
                                        "Name": element.Name,
                                        "Cost_Time": element.Cost_Time,
                                        "Plan_State": element.Plan_State,
                                        "Plan_Count": element.Plan_Count,
                                        "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                                        "Element_Cost": bundle_item.Element_Cost
                                    })
                                
                                else:   # 시퀀스에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                                    raise HTTPException(status_code=404, detail=f"시퀀스 내 번들 시술 정보를 찾을 수 없습니다. (Element_ID: {bundle_item.Element_ID})")
                    
                    # Custom_ID가 있는 경우 (Custom - Element 단위로 분할)
                    elif sequence_item.Custom_ID:
                        custom_list = db.query(ProcedureCustom).filter(
                            ProcedureCustom.GroupID == sequence_item.Custom_ID
                        ).all()
                        
                        if not custom_list:
                            raise HTTPException(status_code=404, detail=f"시퀀스 내 커스텀 정보를 찾을 수 없습니다. (Custom_ID: {sequence_item.Custom_ID})")
                        
                        for custom_item in custom_list:
                            if custom_item.Element_ID:
                                element = db.query(ProcedureElement).filter(
                                    ProcedureElement.ID == custom_item.Element_ID
                                ).first()
                                
                                if element:
                                    step_details["elements"].append({
                                        "Class_Major": element.Class_Major,
                                        "Class_Sub": element.Class_Sub,
                                        "Class_Detail": element.Class_Detail,
                                        "Class_Type": element.Class_Type,
                                        "Name": element.Name,
                                        "Cost_Time": element.Cost_Time,
                                        "Plan_State": element.Plan_State,
                                        "Plan_Count": element.Plan_Count,
                                        "Plan_Interval": element.Plan_Interval,  # 시술 재방문 주기 추가
                                        "Custom_Count": custom_item.Custom_Count,
                                        "Element_Limit": custom_item.Element_Limit,
                                        "Element_Cost": custom_item.Element_Cost
                                    })
                                
                                else:   # 시퀀스에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                                    raise HTTPException(status_code=404, detail=f"시퀀스 내 커스텀 시술 정보를 찾을 수 없습니다. (Element_ID: {custom_item.Element_ID})")
                    
                    # 시퀀스에 포함된 Element의 정보가 있는 경우 저장
                    if step_details["elements"]:
                        sequence_details.append(step_details)
                    
                    else:   # 시퀀스에 포함된 Element의 정보를 찾을 수 없을 경우 (예외처리)
                        raise HTTPException(status_code=404, detail=f"시퀀스 내 시술 정보를 찾을 수 없습니다. (Element_ID: {sequence_item.Element_ID})")
                
                # 시퀀스에 포함된 모든 Element들의 정보를 저장
                if sequence_details:
                    product_data["sequence_details"] = sequence_details
                    
                    # 시퀀스 전체의 재방문 주기 정보 추가
                    if sequence_list and len(sequence_list) > 0:
                        # 첫 번째 시퀀스 항목에서 Sequence_Interval 가져오기
                        first_sequence = sequence_list[0]
                        product_data["sequence_interval"] = first_sequence.Sequence_Interval
                
                else:   # 시퀀스에 포함된 데이터들을 찾을 수 없을 경우 (예외처리)
                    raise HTTPException(status_code=404, detail="시퀀스에 포함된 시술 정보가 없습니다.")
            else:
                raise HTTPException(status_code=404, detail="시퀀스 ID가 없습니다.")
        
        # 상품 상세 조회 완료 message 및 데이터 반환
        return {
            "status": "success",
            "message": "상품 상세 조회 완료",
            "data": product_data
        }
        
    except HTTPException:
        raise
    
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"상품 상세 조회 중 오류 발생: {str(e)}"
        )