"""
    Read API 상세 조회 서비스
    상품 상세 조회에 필요한 Element, Bundle, Custom, Sequence 상세 정보 조회 비즈니스 로직
"""

from sqlalchemy.orm import Session
from fastapi import HTTPException
from typing import Dict, Any
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence

""" Package_Type별 상세 정보 추가 """
def add_package_details(product, product_data: Dict[str, Any], db: Session):
    
    # 단일시술 상세 정보 추가
    if product.Package_Type == "단일시술":
        add_element_details(product, product_data, db)
    
    # 번들 상세 정보 추가
    elif product.Package_Type == "번들":
        add_bundle_details(product, product_data, db)
    
    # 커스텀 상세 정보 추가
    elif product.Package_Type == "커스텀":
        add_custom_details(product, product_data, db)
    
    # 시퀀스 상세 정보 추가
    elif product.Package_Type == "시퀀스":
        add_sequence_details(product, product_data, db)


""" 단일시술 상세 정보 추가 """
def add_element_details(product, product_data: Dict[str, Any], db: Session):
    
    if not product.Element_ID:
        raise HTTPException(status_code=404, detail="단일시술을 찾을 수 없습니다.")
    
    element = db.query(ProcedureElement).filter(
        ProcedureElement.ID == product.Element_ID
    ).first()
    
    if not element:
        raise HTTPException(status_code=404, detail=f"시술 정보를 찾을 수 없습니다. (Element_ID: {product.Element_ID})")
    
    # 단일시술 상세 정보 추가
    product_data["element_details"] = {
        "Class_Major": element.Class_Major,
        "Class_Sub": element.Class_Sub,
        "Class_Detail": element.Class_Detail,
        "Class_Type": element.Class_Type,
        "Name": element.Name,
        "Cost_Time": element.Cost_Time,
        "Plan_State": element.Plan_State,
        "Plan_Count": element.Plan_Count,
        "Plan_Interval": element.Plan_Interval,
        "Element_Cost": element.Price
    }


""" 번들 상세 정보 추가 """
def add_bundle_details(product, product_data: Dict[str, Any], db: Session):
    
    if not product.Bundle_ID:
        raise HTTPException(status_code=404, detail="번들 ID가 없습니다.")
    
    bundle_list = db.query(ProcedureBundle).filter(
        ProcedureBundle.GroupID == product.Bundle_ID
    ).order_by(ProcedureBundle.ID).all()
    
    if not bundle_list:
        raise HTTPException(status_code=404, detail="번들 정보를 찾을 수 없습니다.")
    
    bundle_details = []
    bundle_name = None
    
    # bundle_list가 있을 경우, 내부의 모든 bundle_item를 순회하면서 bundle_details를 생성
    for bundle_item in bundle_list:
        if bundle_item.ID == 1:
            bundle_name = bundle_item.Name
        
        if bundle_item.Element_ID:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == bundle_item.Element_ID
            ).first()
            
            if not element:
                raise HTTPException(status_code=404, detail=f"번들 내 시술 정보를 찾을 수 없습니다. (Element_ID: {bundle_item.Element_ID})")
            
            # bundle_details에 번들 상세 정보 추가
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
                    "Plan_Interval": element.Plan_Interval,
                    "Element_Cost": element.Price
                }
            })
    
    if not bundle_name:
        raise HTTPException(status_code=404, detail="번들 이름을 찾을 수 없습니다.")
    
    if not bundle_details:
        raise HTTPException(status_code=404, detail="번들에 포함된 시술 정보가 없습니다.")
    
    # product_data에 번들 이름과 상세 정보 추가
    product_data["bundle_name"] = bundle_name
    product_data["bundle_details"] = bundle_details


""" 커스텀 상세 정보 추가 """
def add_custom_details(product, product_data: Dict[str, Any], db: Session):
    
    if not product.Custom_ID:
        raise HTTPException(status_code=404, detail="커스텀 ID가 없습니다.")
    
    custom_list = db.query(ProcedureCustom).filter(
        ProcedureCustom.GroupID == product.Custom_ID
    ).all()
    
    if not custom_list:
        raise HTTPException(status_code=404, detail="커스텀 정보를 찾을 수 없습니다.")
    
    custom_details = []
    custom_name = None
    
    # custom_list가 있을 경우, 내부의 모든 custom_item를 순회하면서 custom_details를 생성
    for custom_item in custom_list:
        if custom_item.ID == 1:
            custom_name = custom_item.Name
        
        if custom_item.Element_ID:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == custom_item.Element_ID
            ).first()
            
            if not element:
                raise HTTPException(status_code=404, detail=f"커스텀 내 시술 정보를 찾을 수 없습니다. (Element_ID: {custom_item.Element_ID})")
            
            # custom_details에 커스텀 상세 정보 추가
            custom_details.append({
                "ID": custom_item.ID,
                "Element_ID": custom_item.Element_ID,
                "Custom_Count": custom_item.Custom_Count,
                "Element_Limit": custom_item.Element_Limit,
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
                    "Plan_Interval": element.Plan_Interval,
                    "Element_Cost": element.Price
                }
            })
    
    if not custom_name:
        raise HTTPException(status_code=404, detail="커스텀 이름을 찾을 수 없습니다.")
    
    if not custom_details:
        raise HTTPException(status_code=404, detail="커스텀에 포함된 시술 정보가 없습니다.")
    
    # product_data에 커스텀 이름과 상세 정보 추가
    product_data["custom_name"] = custom_name
    product_data["custom_details"] = custom_details


""" 시퀀스 상세 정보 추가 """
def add_sequence_details(product, product_data: Dict[str, Any], db: Session):
    
    if not product.Sequence_ID:
        raise HTTPException(status_code=404, detail="시퀀스 ID가 없습니다.")
    
    sequence_list = db.query(ProcedureSequence).filter(
        ProcedureSequence.GroupID == product.Sequence_ID
    ).order_by(ProcedureSequence.Step_Num).all()
    
    if not sequence_list:
        raise HTTPException(status_code=404, detail="시퀀스 정보를 찾을 수 없습니다.")
    
    sequence_details = []
    
    # sequence_list가 있을 경우, 내부의 모든 sequence_item를 순회하면서 step_details를 생성
    for sequence_item in sequence_list:
        step_details = {
            "Step_Num": sequence_item.Step_Num,
            "elements": []
        }
        
        # Sequence_item의 Element_ID가 있을 경우, 내부의 element_item를 순회하면서 step_details에 시술 상세 정보 추가
        if sequence_item.Element_ID:
            element = db.query(ProcedureElement).filter(
                ProcedureElement.ID == sequence_item.Element_ID
            ).first()
            
            if not element:
                raise HTTPException(status_code=404, detail=f"시퀀스 내 시술 정보를 찾을 수 없습니다. (Element_ID: {sequence_item.Element_ID})")
            
            # step_details에 시술 상세 정보 추가
            step_details["elements"].append({
                "Class_Major": element.Class_Major,
                "Class_Sub": element.Class_Sub,
                "Class_Detail": element.Class_Detail,
                "Class_Type": element.Class_Type,
                "Name": element.Name,
                "Cost_Time": element.Cost_Time,
                "Plan_State": element.Plan_State,
                "Plan_Count": element.Plan_Count,
                "Plan_Interval": element.Plan_Interval,
                "Element_Cost": element.Price
            })
        

        # Sequence_item의 Bundle_ID가 있을 경우, 내부의 bundle_item를 순회하면서 step_details에 번들 상세 정보 추가
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
                    
                    if not element:
                        raise HTTPException(status_code=404, detail=f"시퀀스 내 번들 시술 정보를 찾을 수 없습니다. (Element_ID: {bundle_item.Element_ID})")
                    
                    step_details["elements"].append({
                        "Class_Major": element.Class_Major,
                        "Class_Sub": element.Class_Sub,
                        "Class_Detail": element.Class_Detail,
                        "Class_Type": element.Class_Type,
                        "Name": element.Name,
                        "Cost_Time": element.Cost_Time,
                        "Plan_State": element.Plan_State,
                        "Plan_Count": element.Plan_Count,
                        "Plan_Interval": element.Plan_Interval,
                        "Element_Cost": bundle_item.Element_Cost
                    })
        

        # Sequence_item의 Custom_ID가 있을 경우, 내부의 custom_item를 순회하면서 step_details에 커스텀 상세 정보 추가
        elif sequence_item.Custom_ID:
            
            custom_list = db.query(ProcedureCustom).filter(
                ProcedureCustom.GroupID == sequence_item.Custom_ID
            ).all()
            
            if not custom_list:
                raise HTTPException(status_code=404, detail=f"시퀀스 내 커스텀 정보를 찾을 수 없습니다. (Custom_ID: {sequence_item.Custom_ID})")
            
            # custom_list가 있을 경우, 내부의 모든 custom_item를 순회하면서 step_details에 커스텀 상세 정보 추가
            for custom_item in custom_list:
                if custom_item.Element_ID:
                    element = db.query(ProcedureElement).filter(
                        ProcedureElement.ID == custom_item.Element_ID
                    ).first()
                    
                    if not element:
                        raise HTTPException(status_code=404, detail=f"시퀀스 내 커스텀 시술 정보를 찾을 수 없습니다. (Element_ID: {custom_item.Element_ID})")
                    
                    # step_details에 커스텀 상세 정보 추가
                    step_details["elements"].append({
                        "Class_Major": element.Class_Major,
                        "Class_Sub": element.Class_Sub,
                        "Class_Detail": element.Class_Detail,
                        "Class_Type": element.Class_Type,
                        "Name": element.Name,
                        "Cost_Time": element.Cost_Time,
                        "Plan_State": element.Plan_State,
                        "Plan_Count": element.Plan_Count,
                        "Plan_Interval": element.Plan_Interval,
                        "Custom_Count": custom_item.Custom_Count,
                        "Element_Limit": custom_item.Element_Limit,
                        "Element_Cost": custom_item.Element_Cost
                    })
        
        sequence_details.append(step_details)
    
    if not sequence_details:
        raise HTTPException(status_code=404, detail="시퀀스에 포함된 시술 정보가 없습니다.")
    
    product_data["sequence_details"] = sequence_details
    
    # 시퀀스 전체의 재방문 주기 정보 추가
    if sequence_list and len(sequence_list) > 0:
        first_sequence = sequence_list[0]
        product_data["sequence_interval"] = first_sequence.Sequence_Interval
