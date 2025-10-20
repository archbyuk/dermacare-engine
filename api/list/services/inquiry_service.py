"""
    상품 조회 서비스 함수들
"""
from sqlalchemy import desc
from db.session import SessionLocal
from db.models.product import ProductEvent, ProductStandard
from db.models.info import InfoStandard, InfoEvent
from .list_service import process_procedure_data

# Standard 상품 조회 및 처리
def inquiry_standard_products():

    db = SessionLocal()
    
    try:
        
        # 1. JOIN으로 Product + Info 동시 조회
        standard_query_results = db.query(
            ProductStandard, InfoStandard
        ).outerjoin(
            InfoStandard,
            ProductStandard.Standard_Info_ID == InfoStandard.ID
        ).order_by(
            desc(ProductStandard.Standard_Start_Date)
        ).all()
        
        
        # 최종 응답용 리스트
        standard_products_list = []

        # Procedure 데이터를 가져오기 ProductStandard 테이블의 데이터만 가져오기
        query_results_standard_product = []
        
        # Procedure 데이터를 가져오기 위한 ID 수집
        element_ids, bundle_ids, custom_ids, sequence_ids = [], [], [], []
        
        # 기본 정보 구성 + ID 수집
        for standard_product, standard_info in standard_query_results:
            
            # for문이 돌 때마다 순차적으로 리스트에 추가
            query_results_standard_product.append(standard_product)
            
            # Procedure ID 수집
            if standard_product.Element_ID:
                element_ids.append(standard_product.Element_ID)
            
            elif standard_product.Bundle_ID:
                bundle_ids.append(standard_product.Bundle_ID)
            
            elif standard_product.Custom_ID:
                custom_ids.append(standard_product.Custom_ID)
            
            elif standard_product.Sequence_ID:
                sequence_ids.append(standard_product.Sequence_ID)
            
            # 기본 정보만 구성 (procedure_names, class_types 없음!)
            standard_product_data = {
                "ID": standard_product.ID,
                "Product_Type": "standard",
                "Package_Type": standard_product.Package_Type,
                "Sell_Price": standard_product.Sell_Price,
                "Original_Price": standard_product.Original_Price,
                "Product_Name": standard_info.Product_Standard_Name if standard_info else f"Standard {standard_product.ID}",
                "Product_Description": standard_info.Product_Standard_Description if standard_info else f"Description {standard_product.ID}",
                "Precautions": standard_info.Precautions if standard_info else f"Precautions {standard_product.ID}"
            }
            
            standard_products_list.append(standard_product_data)

        # 자, 이제 여기서 1차 응답 완성이고, element~sequence 데이터를 가져오기 위한 ids 배열도 준비가 된 상황.
        
        # Procedure 데이터 조회 및 추가
        if element_ids or bundle_ids or custom_ids or sequence_ids:
            procedure_dict = process_procedure_data(
                db,
                query_results_standard_product,
                element_ids,
                bundle_ids,
                custom_ids,
                sequence_ids
            )
            # procedure_dict: {30030: {"procedure_names": [...], "class_types": [...]}, ...}
            
            # 5. Procedure 정보를 각 상품에 추가 (한 번에 merge)
            for product in standard_products_list:
                product.update(
                    procedure_dict.get(product["ID"], {
                        "procedure_names": [],
                        "class_types": []
                    })
                )
        else:
            # Procedure가 없는 경우 빈 배열 추가
            for product in standard_products_list:
                product.update({
                    "procedure_names": [],
                    "class_types": []
                })
        
        # 6. 최종 응답 반환
        return standard_products_list
    
    finally:
        db.close()


# Event 상품 조회 및 처리
def inquiry_event_products():

    db = SessionLocal()
    
    try:
        
        # 1. JOIN으로 Product + Info 동시 조회
        event_query_results = db.query(
            ProductEvent, InfoEvent
        ).outerjoin(
            InfoEvent,
            ProductEvent.Event_Info_ID == InfoEvent.ID
        ).order_by(
            desc(ProductEvent.Event_Start_Date)
        ).all()
        
        
        # 최종 응답용 리스트
        event_products_list = []

        # Procedure 데이터를 가져오기 ProductEvent 테이블의 데이터만 가져오기
        query_results_event_product = []
        
        # Procedure 데이터를 가져오기 위한 ID 수집
        element_ids, bundle_ids, custom_ids, sequence_ids = [], [], [], []
        
        # 기본 정보 구성 + ID 수집
        for event_product, event_info in event_query_results:
            
            # for문이 돌 때마다 순차적으로 리스트에 추가
            query_results_event_product.append(event_product)
            
            # Procedure ID 수집
            if event_product.Element_ID:
                element_ids.append(event_product.Element_ID)
            
            elif event_product.Bundle_ID:
                bundle_ids.append(event_product.Bundle_ID)
            
            elif event_product.Custom_ID:
                custom_ids.append(event_product.Custom_ID)
            
            elif event_product.Sequence_ID:
                sequence_ids.append(event_product.Sequence_ID)
            
            # 기본 정보만 구성 (procedure_names, class_types 없음!)
            event_product_data = {
                "ID": event_product.ID,
                "Product_Type": "event",
                "Package_Type": event_product.Package_Type,
                "Sell_Price": event_product.Sell_Price,
                "Original_Price": event_product.Original_Price,
                "Product_Name": event_info.Event_Name if event_info else f"Event {event_product.ID}",
                "Product_Description": event_info.Event_Description if event_info else f"Description {event_product.ID}",
                "Precautions": event_info.Precautions if event_info else f"Precautions {event_product.ID}"
            }
            
            event_products_list.append(event_product_data)

        # Procedure 데이터 조회 및 추가
        if element_ids or bundle_ids or custom_ids or sequence_ids:
            procedure_dict = process_procedure_data(
                db,
                query_results_event_product,
                element_ids,
                bundle_ids,
                custom_ids,
                sequence_ids
            )
            
            # Procedure 정보를 각 상품에 추가 (한 번에 merge)
            for product in event_products_list:
                product.update(
                    procedure_dict.get(product["ID"], {
                        "procedure_names": [],
                        "class_types": []
                    })
                )
        else:
            # Procedure가 없는 경우 빈 배열 추가
            for product in event_products_list:
                product.update({
                    "procedure_names": [],
                    "class_types": []
                })
        
        # 최종 응답 반환
        return event_products_list
    
    finally:
        db.close()