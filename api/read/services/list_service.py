"""
    [ Read API 목록 조회 서비스 ]
    상품 목록 조회에 필요한 기본 정보 및 시술 이름 조회 비즈니스 로직
"""

from sqlalchemy.orm import Session
from typing import Dict, Any
from db.models.info import InfoEvent, InfoStandard
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence
from db.models.product import ProductEvent, ProductStandard

""" 스탠다드 상품 데이터 구성 (목록용) """
def build_standard_product_data(standard_product, db: Session) -> Dict[str, Any]:
    
    # 스탠다드 상품 데이터 구성
    standard_product_data = {
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
        
        # info_standard 테이블의 ID랑 standard_product테이블의 Standard_Info_ID가 같은 경우
        standard_info = db.query(InfoStandard).filter(
            InfoStandard.ID == standard_product.Standard_Info_ID
        ).first()
        
        # standard_info 테이블이 있는 경우 데이터 추가
        if standard_info:
            standard_product_data["Product_Name"] = standard_info.Product_Standard_Name
            standard_product_data["Product_Description"] = standard_info.Product_Standard_Description
            standard_product_data["Precautions"] = standard_info.Precautions
        
        # standard_info 테이블이 없는 경우 None 추가
        else:
            standard_product_data["Product_Name"] = None
            standard_product_data["Product_Description"] = None
            standard_product_data["Precautions"] = None
    
    # Standard_Info_ID가 없는 경우 None 추가
    else:
        standard_product_data["Product_Name"] = None
        standard_product_data["Product_Description"] = None
        standard_product_data["Precautions"] = None
    
    # 시술 정보 추가: 시술 이름과 타입만
    procedure_names, class_types = get_procedure_info(standard_product, db)     # 시술 이름과 타입 조회(get_procedure_info 함수 호출)
    
    # product_data에 시술 이름과 타입 추가
    standard_product_data["procedure_names"] = procedure_names           # 상품의 이름
    standard_product_data["procedure_count"] = len(procedure_names)      # 상품의 시술 개수 (상품 이름의 개수)
    standard_product_data["class_types"] = list(                         # 상품의 시술 타입 모음
        set(class_types)
    )
    standard_product_data["class_type_count"] = len(                     # 상품의 시술 타입 개수
        set(class_types)
    )
    
    # 스탠다드 상품 데이터 구성 완료: standard_product_data
    return standard_product_data


""" 이벤트 상품 데이터 구성 (목록용) """
def build_event_product_data(event_product, db: Session) -> Dict[str, Any]:
    
    # 이벤트 상품 데이터 구성
    event_product_data = {
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
        
        # event_info 테이블이 있는 경우 데이터 추가
        if event_info:
            event_product_data["Product_Name"] = event_info.Event_Name
            event_product_data["Product_Description"] = event_info.Event_Description
            event_product_data["Precautions"] = event_info.Precautions
        
        # event_info 테이블이 없는 경우 None 추가
        else:
            event_product_data["Product_Name"] = None
            event_product_data["Product_Description"] = None
            event_product_data["Precautions"] = None
    
    # Event_Info_ID가 없는 경우 None 추가
    else:
        event_product_data["Product_Name"] = None
        event_product_data["Product_Description"] = None
        event_product_data["Precautions"] = None
    
    # 시술 정보 추가: 시술 이름과 타입만
    procedure_names, class_types = get_procedure_info(event_product, db)        # 시술 이름과 타입 조회(get_procedure_info 함수 호출)
    
    # event_product_data에 시술 이름과 타입 추가
    event_product_data["procedure_names"] = procedure_names           # 상품의 이름
    event_product_data["procedure_count"] = len(procedure_names)      # 상품의 시술 개수 (상품 이름의 개수)
    event_product_data["class_types"] = list(                         # 상품의 시술 타입 모음
        set(class_types)
    )
    event_product_data["class_type_count"] = len(                     # 상품의 시술 타입 개수
        set(class_types)
    )
    
    # 이벤트 상품 데이터 구성 완료: event_product_data
    return event_product_data


""" 시술 이름과 타입 조회 (목록용) """
def get_procedure_info(product, db: Session) -> tuple[list[str], list[str]]:
    
    try:    
        # 시술 이름과 타입을 저장하는 리스트
        procedure_names = []
        class_types = []
    
        ### 1. 단일 시술 (Element_ID)
        if product.Element_ID:
            
            # element 테이블의 ID랑 product테이블의 Element_ID가 같은 경우
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == product.Element_ID
            ).first()
            
            # element 테이블이 있는 경우 데이터 추가
            if element:
                procedure_names.append(element.Name)
                
                # element 테이블의 Class_Type이 있는 경우 추가
                if element.Class_Type:
                    class_types.append(element.Class_Type)
        
        
        ### 2. 번들 시술 (Bundle_ID)
        elif product.Bundle_ID:
            
            # bundle 테이블의 GroupID랑 product테이블의 Bundle_ID가 같은 경우
            bundle_elements = db.query(ProcedureElement).join(
                ProcedureBundle, ProcedureElement.ID == ProcedureBundle.Element_ID
            ).filter(
                ProcedureBundle.GroupID == product.Bundle_ID
            ).all()
            
            # bundle_elements 테이블이 있는 경우 데이터 추가
            for element in bundle_elements:
                procedure_names.append(element.Name)
                
                # element 테이블의 Class_Type이 있는 경우 추가
                if element.Class_Type:
                    class_types.append(element.Class_Type)
        

        ### 3. 커스텀 시술 (Custom_ID)
        elif product.Custom_ID:
            
            # custom_elements 테이블의 GroupID랑 product테이블의 Custom_ID가 같은 경우
            custom_elements = db.query(ProcedureElement).join(
                ProcedureCustom, ProcedureElement.ID == ProcedureCustom.Element_ID
            ).filter(
                ProcedureCustom.GroupID == product.Custom_ID
            ).all()
            
            for element in custom_elements:
                procedure_names.append(element.Name)
                if element.Class_Type:
                    class_types.append(element.Class_Type)
        

        ### 4. 시퀀스 시술 (Sequence_ID)
        elif product.Sequence_ID:
            
            # sequence_elements 테이블의 GroupID랑 product테이블의 Sequence_ID가 같은 경우
            sequence_elements = db.query(ProcedureElement).join(
                ProcedureSequence, ProcedureElement.ID == ProcedureSequence.Element_ID
            ).filter(
                ProcedureSequence.GroupID == product.Sequence_ID
            ).all()
            
            for element in sequence_elements:
                procedure_names.append(element.Name)
                if element.Class_Type:
                    class_types.append(element.Class_Type)
        
            
        # 시술 이름과 타입을 반환
        return procedure_names, class_types
        
    except Exception as e:
        # 오류 발생 시 빈 리스트 반환
        return [], []
