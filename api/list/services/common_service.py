"""
    [ Read API 공통 서비스 ]
    상품 조회 및 기본 정보 구성 관련 공통 비즈니스 로직
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Dict, Any
from db.models.info import InfoEvent, InfoStandard
from db.models.product import ProductEvent, ProductStandard


""" 상품 타입에 따른 상품 조회를 위한 검증 함수 """
def get_product_by_type(product_id: int, product_type: str, db: Session):
    
    # standard 상품 조회
    if product_type == "standard":
        product = db.query(ProductStandard).filter(ProductStandard.ID == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="상품을 찾을 수 없습니다.")
    
    # event 상품 조회
    elif product_type == "event":
        product = db.query(ProductEvent).filter(ProductEvent.ID == product_id).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="이벤트를 찾을 수 없습니다.")
    
    # 잘못된 상품 타입인 경우
    else:
        raise HTTPException(status_code=400, detail="잘못된 상품 타입입니다.")
    
    # 검증 후 상품 데이터 반환
    return product


""" 상품 기본 정보 구성 (상세 조회용) """
def build_product_basic_info(product, product_type: str, db: Session) -> Dict[str, Any]:
    
    # 상품 기본 정보 구성
    product_data = {
        "ID": product.ID,
        "Product_Type": product_type,
        "Package_Type": product.Package_Type,
        "Element_ID": product.Element_ID,
        "Bundle_ID": product.Bundle_ID,
        "Custom_ID": product.Custom_ID,
        "Sequence_ID": product.Sequence_ID,
        "Sell_Price": product.Sell_Price,
        "Original_Price": product.Original_Price,
        "Discount_Rate": product.Discount_Rate,
        "Validity_Period": product.Validity_Period,
        "VAT": product.VAT,
        "Covered_Type": product.Covered_Type,
        "Taxable_Type": product.Taxable_Type
    }
    
    ### 상품 타입에 따른 상품 노출 기간 및 정보 추가 ###
    
    # 스탠다드 상품 데이터일 경우 standard_start_date, standard_end_date 데이터 추가
    if product_type == "standard":
        product_data["Standard_Start_Date"] = product.Standard_Start_Date
        product_data["Standard_End_Date"] = product.Standard_End_Date
        
        # add_standard_info 함수 호출 및 데이터 추가
        add_standard_info(product, product_data, db)
    
    # 이벤트 상품 데이터일 경우 event_start_date, event_end_date 데이터 추가
    elif product_type == "event":
        product_data["Event_Start_Date"] = product.Event_Start_Date
        product_data["Event_End_Date"] = product.Event_End_Date
        
        # add_event_info 함수 호출 및 데이터 추가
        add_event_info(product, product_data, db)
    
    # 상품 기본 정보 구성 완료: Product_Standard or Product_Event
    return product_data


### -------------- 상세 조회용 상품 데이터 추가 functions -------------- ###

""" 스탠다드 상품 데이터 추가 """
def add_standard_info(product, product_data: Dict[str, Any], db: Session):
    
    # Standard_Info_ID가 있는 경우
    if product.Standard_Info_ID:
        
        # info_standard 테이블의 ID랑 product테이블의 Standard_Info_ID가 같은 경우
        standard_info = db.query(InfoStandard).filter(
            InfoStandard.ID == product.Standard_Info_ID
        ).first()
        
        # standard_info 테이블이 있는 경우
        if standard_info:
            product_data["Product_Name"] = standard_info.Product_Standard_Name
            product_data["Product_Description"] = standard_info.Product_Standard_Description
            product_data["Precautions"] = standard_info.Precautions
        
        # standard_info 테이블이 없는 경우
        else:
            product_data["Product_Name"] = None
            product_data["Product_Description"] = None
            product_data["Precautions"] = None
    
    # Standard_Info_ID가 없는 경우
    else:
        product_data["Product_Name"] = None
        product_data["Product_Description"] = None
        product_data["Precautions"] = None


""" 이벤트 상품 데이터 추가 """
def add_event_info(product, product_data: Dict[str, Any], db: Session):
    
    # Event_Info_ID가 있는 경우
    if product.Event_Info_ID:
        
        # info_event 테이블의 ID랑 product테이블의 Event_Info_ID가 같은 경우
        event_info = db.query(InfoEvent).filter(
            InfoEvent.ID == product.Event_Info_ID
        ).first()
        
        # info_event 테이블이 있는 경우
        if event_info:
            product_data["Product_Name"] = event_info.Event_Name
            product_data["Product_Description"] = event_info.Event_Description
            product_data["Precautions"] = event_info.Precautions
        
        # info_event 테이블이 없는 경우
        else:
            product_data["Product_Name"] = f"이벤트 상품 {product.ID}"
            product_data["Product_Description"] = "이벤트 상품 설명이 없습니다."
            product_data["Precautions"] = "주의사항이 없습니다."
    
    # Event_Info_ID가 없는 경우
    else:
        product_data["Product_Name"] = f"이벤트 상품 {product.ID}"
        product_data["Product_Description"] = "이벤트 상품 설명이 없습니다."
        product_data["Precautions"] = "주의사항이 없습니다."
