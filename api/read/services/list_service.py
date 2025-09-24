"""
    [ Read API 목록 조회 서비스 - 최적화 버전 ]
    N+1 쿼리 문제를 해결한 최적화된 상품 목록 조회 비즈니스 로직
"""

from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from typing import Dict, Any, List
from db.models.info import InfoEvent, InfoStandard
from db.models.procedure import ProcedureElement, ProcedureBundle, ProcedureCustom, ProcedureSequence
from db.models.product import ProductEvent, ProductStandard
from pprint import pprint

""" 상품에서 시술 ID들을 수집하는 공통 함수 """
def collect_procedure_ids(products: List[Any]) -> tuple[List[int], List[int], List[int], List[int]]:
    """상품 리스트에서 시술 ID들을 수집하여 반환"""
    element_ids = []
    bundle_ids = []
    custom_ids = []
    sequence_ids = []
    
    # products 리스트를 순회하면서 시술 ID들을 수집
    for product in products:
        
        if product.Element_ID:
            element_ids.append(product.Element_ID)
        
        elif product.Bundle_ID:
            bundle_ids.append(product.Bundle_ID)
        
        elif product.Custom_ID:
            custom_ids.append(product.Custom_ID)
        
        elif product.Sequence_ID:
            sequence_ids.append(product.Sequence_ID)
    
    return element_ids, bundle_ids, custom_ids, sequence_ids


""" 시술 정보를 조회하고 결과에 추가하는 공통 함수: 아무것도 반환하지 않는 함수 """
def process_procedure_data(
    db: Session, 
    products: List[Any], 
    element_ids: List[int], 
    bundle_ids: List[int], 
    custom_ids: List[int], 
    sequence_ids: List[int], 
    result: Dict[int, Dict[str, Any]]
) -> None:
    
    # 1. Element 시술 정보 일괄 조회: element Name, Class_Type 추가 완
    if element_ids:
        elements = db.query(ProcedureElement).filter(ProcedureElement.ID.in_(element_ids)).all()
        element_dict = {
            e.ID: e for e in elements
        }
        # element_dict: {
        #   1: <ProcedureElement(ID=1, Name='시술1')>, 
        #   2: <ProcedureElement(ID=2, Name='시술2')>
        # }
        
        # 상품의 ID와 Element_ID가 같은 경우 시술 정보를 조회하기 위한 for문
        for product in products:
            # product의 Element_ID와 element_dict의 ID가 같을 경우,
            if product.Element_ID and product.Element_ID in element_dict:
                # product의 Element_ID를 element_dict의 ID와 매칭시켜 해당 데이터를 element에 담기: element = element_dict[10] >> <ProcedureElement(ID=10, Name='시술1')>
                element = element_dict[product.Element_ID]

                # result의 key = product_id의 value에 있는 procedure_names 리스트에 element.Name을 추가
                result[product.ID]["procedure_names"].append(element.Name)
                # result의 key = product_id의 value에 있는 class_types 리스트에 element.Class_Type을 추가 (Optional)
                if element.Class_Type:
                    result[product.ID]["class_types"].append(element.Class_Type)

            # element_ids 조회 완료 result: {1: {'procedure_names': ['시술'], 'class_types': []}}
    

    # 2. Bundle 시술 정보 일괄 조회: element Name, Class_Type 추가 완
    if bundle_ids:
        # ProcedureElement랑 ProcedureBundle 테이블을 조인하여 bundle_ids에 있는 GroupID와 같은 데이터를 조회 (Bundle의 Element_ID와 Elmenet의 ID가 같은 경우)
        bundle_elements = db.query(
            ProcedureElement,
            ProcedureBundle.GroupID
        ).join(
            ProcedureBundle, ProcedureElement.ID == ProcedureBundle.Element_ID
        ).filter(ProcedureBundle.GroupID.in_(bundle_ids)).all()

        # [ 쿼리 결과 ]
        #     bundle_elements = [
        #       (<ProcedureElement(ID=11000)>, 10020),  => 시술 11000이 Bundle GroupID 10020에 속함
        #       (<ProcedureElement(ID=11000)>, 10060),  => 시술 11000이 Bundle GroupID 10060에도 속함
        #       (<ProcedureElement(ID=11010)>, 10140),  => 시술 11010이 Bundle GroupID 10140에 속함
        #     ]
                            
        # bundle_elements: (<ProcedureElement(ID = int, Name = 'string')>, GroupID:int)

        # Bundle ID별로 그룹화: key: GroupID, value: ProcedureElement Object List
        bundle_dict = {}
        # bundle_dict = {
        #    1: [
        #        <ProcedureElement(ID=1, Name='시술1')>, 
        #        <ProcedureElement(ID=2, Name='시술2')>
        #    ], 
        #    
        #    2: [
        #        <ProcedureElement(ID=3, Name='시술3')>
        #    ]
        # }

        
        # bundle_elements 안에 모든 element를 순회하면서 bundle_dict에 추가
        for element, group_id in bundle_elements:
            # bundle_dict에 element_group.GroupID가 없는 경우, 빈 리스트 반환
            if group_id not in bundle_dict:
                bundle_dict[group_id] = []

            # element_group.GroupID를 key로 하는 리스트에 element_group을 추가: GroupID를 기준으로 그룹화
            bundle_dict[group_id].append(element)
            
            # [ 그룹화 결과 ]
            #   bundle_dict = {
            #      10020: [
            #          (<ProcedureElement(ID=11000)>, 10020),
            #          (<ProcedureElement(ID=11040)>, 10020)
            #      ],
            #      
            #       10060: [
            #          (<ProcedureElement(ID=11000)>, 10060)
            #      ]
            #    }

        
        # 상품의 ID와 Bundle_ID가 같은 경우 시술 정보를 조회하기 위한 for문
        for product in products:
            # 상품의 Bundle_ID와 bundle_dict의 key(GroupID)가 같은 경우, 시술 정보를 조회하기 위한 if문
            if product.Bundle_ID and product.Bundle_ID in bundle_dict:
                # bundle_dict[product.Bundle_ID]의 모든 element와 _group_id를 순회하면서 result에 추가 (group_id는 tuple 언패킹을 위한 _변수)
                for element in bundle_dict[product.Bundle_ID]:
                    # result의 key = product_id의 value에 있는 procedure_names 리스트에 element.Name을 추가
                    result[product.ID]["procedure_names"].append(element.Name)
                    
                    # result의 key = product_id의 value에 있는 class_types 리스트에 element.Class_Type을 추가 (Optional)
                    if element.Class_Type and element.Class_Type not in result[product.ID]["class_types"]:
                        result[product.ID]["class_types"].append(element.Class_Type)
            
            # bundle_ids 조회 완료 result: {1: {'procedure_names': ['시술1', '시술2'], 'class_types': []}}
    

    # 3. Custom 시술 정보 일괄 조회: element Name, Class_Type 추가 완
    if custom_ids:
        # ProcedureElement와 ProcedureCustom 테이블을 조인하여 custom_ids에 있는 GroupID와 같은 데이터를 조회 (Custom의 Element_ID와 Elmenet의 ID가 같은 경우)
        custom_elements = db.query(
            ProcedureElement,
            ProcedureCustom.GroupID
        ).join(
            ProcedureCustom, ProcedureElement.ID == ProcedureCustom.Element_ID
        ).filter(ProcedureCustom.GroupID.in_(custom_ids)).all()

        # [ 쿼리 결과 ]
        #   custom_elements = [
        #       (<ProcedureElement(ID=74140, Name='재생관리 1회')>, 10010),
        #       (<ProcedureElement(ID=74140, Name='재생관리 1회')>, 10020),
        #       (<ProcedureElement(ID=74140, Name='재생관리 1회')>, 10030),
        #       (<ProcedureElement(ID=74170, Name='오멜론 LED')>, 10030),
        #       (<ProcedureElement(ID=74180, Name='클랜징')>, 10030),
        #       (<ProcedureElement(ID=90000, Name='모델링팩')>, 10030),
        #       (<ProcedureElement(ID=90000, Name='모델링팩')>, 10030)
        #   ]
        
        # custom_elements 안에 모든 element를 순회하면서 추가할 딕셔너리 생성
        custom_dict = {}
        
        # custom_dict: key: GroupID, value: ProcedureElement Object List
        for element, group_id in custom_elements:
            
            # custom_dict에 custom_id가 없는 경우, 빈 리스트 반환
            if group_id not in custom_dict:
                custom_dict[group_id] = []
            
            # custom_dict에 group_id를 key로 하는 리스트에 element를 추가
            custom_dict[group_id].append(element)

            # [ 그룹화 결과 ]
            #   custom_dict = {
            #      20040: [
            #          <ProcedureElement(ID=20000, Name='포텐자 모공')>,
            #          <ProcedureElement(ID=20090, Name='디오레 피부재생 1회')>,
            #          <ProcedureElement(ID=20190, Name='피코슈어 부분토닝 1회')>,
            #          <ProcedureElement(ID=20340, Name='엑셀V플러스 홍조 1회')>,
            #      ],
            #      
            #      20050: [
            #          <ProcedureElement(ID=20000, Name='아쿠아포텐자')>,
            #          <ProcedureElement(ID=20090, Name='아쿠아디오레 피부재생 1회')>,
            #          <ProcedureElement(ID=20190, Name='아쿠아슈어 부분토닝 1회')>,
            #          <ProcedureElement(ID=20340, Name='아쿠아V플러스 홍조 1회')>,
            #      ]
            #   }
        
        # 상품의 Custom_ID와 custom_dict의 key(GroupID)가 같은 경우 시술 정보를 조회하기 위한 for문
        for product in products:
            
            # custom_dict에 product.Custom_ID가 있는 경우 시술 정보를 조회하기 위한 if문
            if product.Custom_ID and product.Custom_ID in custom_dict:
                
                # custom_dict[product.Custom_ID]의 모든 element를 순회하면서 result에 추가 (group_id는 tuple 언패킹을 위한 _변수)
                for element in custom_dict[product.Custom_ID]:
                    result[product.ID]["procedure_names"].append(element.Name)
                    
                    # result의 key = product_id의 value에 있는 class_types 리스트에 element.Class_Type을 추가 (Optional)
                    if element.Class_Type and element.Class_Type not in result[product.ID]["class_types"]:
                        result[product.ID]["class_types"].append(element.Class_Type)

        
        # custom_ids 조회 완료 result: {1: {'procedure_names': ['시술1', '시술2'], 'class_types': []}}
    

    # 4. Sequence 시술 정보 일괄 조회: element Name, Class_Type 추가 완
    if sequence_ids:
        sequence_elements = db.query(
            ProcedureElement,
            ProcedureSequence.GroupID
        ).join(
            ProcedureSequence, ProcedureElement.ID == ProcedureSequence.Element_ID
        ).filter(ProcedureSequence.GroupID.in_(sequence_ids)).all()

        # [ 쿼리 결과 ]
        # sequence_elements = [
        #     (<ProcedureElement(ID=20010, Name='포텐자 모공 3회')>, 180),
        #     (<ProcedureElement(ID=20010, Name='포텐자 모공 3회')>, 180),
        # ]

        # sequence_elements: (<ProcedureElement(ID = int, Name = 'string')>, GroupID:int)

        # Sequence ID별로 그룹화: key: GroupID, value: ProcedureElement Object List
        sequence_dict = {}

        # sequence_elements 안에 Tuple을 element, group_id로 언패킹하여 나누고,
        for element, group_id in sequence_elements:
            
            # sequence_dict에 group_id가 없는 경우, 빈 리스트 반환
            if group_id not in sequence_dict:
                sequence_dict[group_id] = []
            
            # sequence_dict에 sequence_id를 key로 하는 리스트에 element를 추가
            sequence_dict[group_id].append(element)
        
        # sequence_dict 그룹화 완료
        # sequence_dict = {
        #     180: [
        #         <ProcedureElement(ID=20010, Name='포텐자 모공 3회')>,
        #         <ProcedureElement(ID=20010, Name='포텐자 모공 흐하하')>,
        #     ],
        #     
        #     181: [
        #         <ProcedureElement(ID=20010, Name='포텐자 모공 1회')>,
        #         <ProcedureElement(ID=20010, Name='포텐자 모공 찡긋')>,
        #     ],
        # }
        

        # 상품의 Sequence_ID와 sequence_dict의 key(GroupID)가 같은 경우 시술 정보를 조회하기 위한 for문
        for product in products:
            
            # 상품의 Sequence_ID와 sequence_dict의 key(GroupID)가 같은 경우 시술 정보를 조회하기 위한 if문
            if product.Sequence_ID and product.Sequence_ID in sequence_dict:
                
                # sequence_dict[product.Sequence_ID]의 모든 element를 순회하면서 result에 추가
                for element in sequence_dict[product.Sequence_ID]:
                    # result의 key = product_id의 value에 있는 procedure_names 리스트에 element.Name을 추가
                    result[product.ID]["procedure_names"].append(element.Name)
                    
                    if element.Class_Type and element.Class_Type not in result[product.ID]["class_types"]:
                        result[product.ID]["class_types"].append(element.Class_Type)
    
        # sequence_ids 조회 완료 result: {1: {'procedure_names': ['시술1', '시술2'], 'class_types': []}}


""" 시술 정보 일괄 조회 함수 """
def get_procedures_batch_optimized(db: Session, product_ids: List[int], product_type: str) -> Dict[int, Dict[str, Any]]:
    
    if not product_ids:
        return {}
    
    result = {
        product_id: {
            "procedure_names": [], 
            "class_types": []
        } 
        for product_id in product_ids
    }
    
    try:
        # 상품 타입에 따른 초기 쿼리만 분기 처리
        if product_type == "standard":
            products = db.query(ProductStandard).filter(ProductStandard.ID.in_(product_ids)).all()
        
        elif product_type == "event":
            products = db.query(ProductEvent).filter(ProductEvent.ID.in_(product_ids)).all()
        
        else:
            return result
        
        # 시술 ID들 수집
        element_ids, bundle_ids, custom_ids, sequence_ids = collect_procedure_ids(products)
        
        # 시술 정보 조회 및 결과 추가 (공통 로직)
        process_procedure_data(db, products, element_ids, bundle_ids, custom_ids, sequence_ids, result)
        
        return result
        
    except Exception as e:
        print(f"시술 정보 일괄 조회 중 오류: {str(e)}")
        
        return result



""" 최적화된 스탠다드 상품 데이터 구성 """
def build_standard_products_optimized(standard_products, db: Session) -> List[Dict[str, Any]]:
    
    if not standard_products:
        return []
    
    # 1. 모든 Standard_Info_ID 수집
    standard_info_ids = [p.Standard_Info_ID for p in standard_products if p.Standard_Info_ID]
    
    # 2. Product_Name 배치 조회
    standard_info_dict = {}
    if standard_info_ids:
        standard_infos = db.query(InfoStandard).filter(InfoStandard.ID.in_(standard_info_ids)).all()
        standard_info_dict = {info.ID: info.Product_Standard_Name for info in standard_infos}
    
    # 3. 시술 정보 배치 조회
    element_ids, bundle_ids, custom_ids, sequence_ids = collect_procedure_ids(standard_products)
    
    # 시술 정보 처리용 결과 딕셔너리
    procedure_result = {
        product.ID: {
            "procedure_names": [], 
            "class_types": []
        } 
        for product in standard_products
    }
    
    # 시술 정보 조회 및 결과 추가
    if element_ids or bundle_ids or custom_ids or sequence_ids:
        process_procedure_data(db, standard_products, element_ids, bundle_ids, custom_ids, sequence_ids, procedure_result)
    
    # 4. 상품 데이터 구성
    products = []
    for standard_product in standard_products:
        product_data = {
            "ID": standard_product.ID,
            "Product_Type": "standard",
            "Package_Type": standard_product.Package_Type,
            "Sell_Price": standard_product.Sell_Price,
            "Original_Price": standard_product.Original_Price
        }
        
        # Product_Name 추가
        if standard_product.Standard_Info_ID and standard_product.Standard_Info_ID in standard_info_dict:
            product_data["Product_Name"] = standard_info_dict[standard_product.Standard_Info_ID]
            print("존재하는 product_name:", product_data["Product_Name"])
        
        else:
            product_data["Product_Name"] = f"시술 {standard_product.ID}"
        
        # 시술 정보 추가 (class_types만, 처음 3개만)
        procedure_data = procedure_result.get(standard_product.ID, {})
        class_types = list(set(procedure_data.get("class_types", [])))[:3]
        product_data.update({
            "class_types": class_types,
        })
        
        products.append(product_data)
    
    return products


""" 최적화된 이벤트 상품 데이터 구성 """
def build_event_products_optimized(event_products, db: Session) -> List[Dict[str, Any]]:
    
    if not event_products:
        return []
    
    # 1. 모든 Event_Info_ID 수집
    event_info_ids = [p.Event_Info_ID for p in event_products if p.Event_Info_ID]
    
    # 2. Product_Name 배치 조회
    event_info_dict = {}
    if event_info_ids:
        event_infos = db.query(InfoEvent).filter(InfoEvent.ID.in_(event_info_ids)).all()
        event_info_dict = {info.ID: info.Event_Name for info in event_infos}
    
    # 3. 시술 정보 배치 조회
    element_ids, bundle_ids, custom_ids, sequence_ids = collect_procedure_ids(event_products)
    
    # 시술 정보 처리용 결과 딕셔너리
    procedure_result = {
        product.ID: {
            "procedure_names": [], 
            "class_types": []
        } 
        for product in event_products
    }
    
    # 시술 정보 조회 및 결과 추가
    if element_ids or bundle_ids or custom_ids or sequence_ids:
        process_procedure_data(db, event_products, element_ids, bundle_ids, custom_ids, sequence_ids, procedure_result)
    
    # 4. 상품 데이터 구성
    products = []
    for event_product in event_products:
        product_data = {
            "ID": event_product.ID,
            "Product_Type": "event",
            "Package_Type": event_product.Package_Type,
            "Sell_Price": event_product.Sell_Price,
            "Original_Price": event_product.Original_Price
        }
        
        # Product_Name 추가
        if event_product.Event_Info_ID and event_product.Event_Info_ID in event_info_dict:
            product_data["Product_Name"] = event_info_dict[event_product.Event_Info_ID]
        else:
            product_data["Product_Name"] = f"이벤트 {event_product.ID}"
        
        # 시술 정보 추가 (class_types만, 처음 3개만)
        procedure_data = procedure_result.get(event_product.ID, {})
        class_types = list(set(procedure_data.get("class_types", [])))[:3]
        product_data.update({
            "class_types": class_types,
        })
        
        products.append(product_data)
    
    return products